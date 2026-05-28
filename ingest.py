import os
import glob
import logging
import hashlib
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GovGPT-Ingest")

# File hash tracking for incremental updates
HASH_FILE = os.path.join(os.path.dirname(__file__), "chroma_db", "file_hashes.json")


def get_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file for change detection."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def load_file_hashes() -> dict:
    """Load existing file hashes from JSON file."""
    if os.path.exists(HASH_FILE):
        try:
            with open(HASH_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load hash file: {e}")
    return {}


def save_file_hashes(hashes: dict):
    """Save file hashes to JSON file."""
    try:
        os.makedirs(os.path.dirname(HASH_FILE), exist_ok=True)
        with open(HASH_FILE, 'w') as f:
            json.dump(hashes, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save hash file: {e}")


def extract_text_from_file(file_path: str) -> str:
    """Extract text from .txt or .pdf files."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.txt':
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    elif ext == '.pdf':
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except ImportError:
            logger.error("pypdf not installed. Run: pip install pypdf")
            return ""
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""
    
    else:
        logger.warning(f"Unsupported file type: {ext}")
        return ""


def ingest_data(force_reingest: bool = False):
    """
    Reads all text and PDF files in the data/ directory, chunks them,
    and ingests them into ChromaDB using the new google-genai SDK.
    Supports incremental updates by tracking file hashes.
    
    Args:
        force_reingest: If True, reprocess all files regardless of changes
    """
    # Check for API Key first
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.startswith("YOUR_"):
        logger.error("❌ ERROR: GEMINI_API_KEY is missing or invalid in .env")
        logger.error("Please get a key from https://aistudio.google.com/ and update .env")
        return False

    try:
        import chromadb
        from google import genai
        from google.genai import types
    except ImportError:
        logger.error("❌ ERROR: Required packages missing. Please ensure chromadb and google-genai are installed.")
        return False

    # BUG FIX (ingest.py): The original code did:
    #   client = genai.Client(api_key=api_key)      ← gemini client
    #   client = chromadb.PersistentClient(...)      ← immediately overwrites it!
    # Then later called client.models.embed_content() on the ChromaDB client
    # object, which has no `.models` attribute → AttributeError crash.
    # Fix: use distinct variable names for each client.

    # Configure Gemini client
    gemini_client = genai.Client(api_key=api_key)

    # Initialize ChromaDB client (persistent) — separate variable
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    logger.info(f"Initializing ChromaDB at: {db_path}")

    try:
        chroma_client = chromadb.PersistentClient(path=db_path)
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        logger.error("Try deleting the 'chroma_db' folder and running ingest again.")
        return False

    # Get or create collection
    collection_name = "gov_schemes"
    try:
        collection = chroma_client.get_or_create_collection(name=collection_name)
        logger.info(f"Connected to collection: {collection_name}")
    except Exception as e:
        logger.error(f"Failed to get/create collection: {e}")
        return False

    # Load existing file hashes for incremental updates
    file_hashes = load_file_hashes() if not force_reingest else {}

    # Find scheme files (both .txt and .pdf)
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    if not os.path.exists(data_dir):
        logger.error(f"Data directory not found at {data_dir}")
        return False

    files = glob.glob(os.path.join(data_dir, "*.txt")) + glob.glob(os.path.join(data_dir, "*.pdf"))
    if not files:
        logger.warning(f"No .txt or .pdf files found in {data_dir}")
        logger.warning("Add scheme files (PM Kisan, MGNREGA, Ayushman Bharat, etc.) to the data/ folder.")
        return False

    logger.info(f"Found {len(files)} scheme files to process.")

    total_chunks = 0
    files_processed = 0
    files_skipped = 0

    for file_path in files:
        filename = os.path.basename(file_path)
        current_hash = get_file_hash(file_path)
        
        # Check if file has changed (skip if unchanged and not forcing reingest)
        if not force_reingest and filename in file_hashes and file_hashes[filename] == current_hash:
            logger.info(f"  ⏭️  Skipping {filename} (unchanged)")
            files_skipped += 1
            continue
        
        logger.info(f"Processing scheme file: {filename}...")

        try:
            # Extract text from file (supports both .txt and .pdf)
            text = extract_text_from_file(file_path)
            if not text:
                logger.warning(f"  No text extracted from {filename}, skipping")
                continue

            # Smart chunking (approx 1500 chars per chunk with 200 overlap)
            chunk_size = 1500
            overlap = 200
            chunks = []

            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))

                if end < len(text):
                    last_newline = text.rfind('\n', start, end)
                    if last_newline != -1 and last_newline > start + (chunk_size // 2):
                        end = last_newline + 1

                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append(chunk_text)
                start = end - overlap

            logger.info(f"  Split into {len(chunks)} chunks. Generating embeddings...")

            # Delete existing chunks for this file if reingesting
            if filename in file_hashes or force_reingest:
                try:
                    existing_ids = [f"{filename}_chunk_{i}" for i in range(1000)]  # Reasonable upper limit
                    collection.delete(ids=existing_ids)
                except Exception as e:
                    logger.debug(f"Could not delete old chunks: {e}")

            for i, chunk in enumerate(chunks):
                doc_id = f"{filename}_chunk_{i}"

                try:
                    # Use gemini_client (not chroma_client) for embeddings
                    result = gemini_client.models.embed_content(
                        model="text-embedding-004",
                        contents=chunk,
                        config=types.EmbedContentConfig(task_type="retrieval_document"),
                    )

                    collection.upsert(
                        documents=[chunk],
                        metadatas=[{"source": filename, "chunk": i}],
                        ids=[doc_id],
                        embeddings=[result.embeddings[0].values]
                    )

                except Exception as e:
                    logger.error(f"  Failed to embed chunk {i}: {e}")

            logger.info(f"  ✅ Successfully ingested {len(chunks)} chunks for {filename}.")
            total_chunks += len(chunks)
            files_processed += 1
            
            # Update file hash
            file_hashes[filename] = current_hash

        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")

    # Save updated file hashes
    save_file_hashes(file_hashes)

    logger.info("==================================================")
    logger.info(f"✅ Database ingestion complete!")
    logger.info(f"   Files processed: {files_processed}")
    logger.info(f"   Files skipped (unchanged): {files_skipped}")
    logger.info(f"   Total chunks: {total_chunks}")
    logger.info("ChromaDB is now ready for GovGPT RAG queries.")
    logger.info("==================================================")
    return True


if __name__ == "__main__":
    ingest_data()