import os
import glob
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GovGPT-Ingest")

def ingest_data():
    """
    Reads all text files in the data/ directory, chunks them,
    and ingests them into ChromaDB using the new google-genai SDK.
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

    # Configure Gemini
    client = genai.Client(api_key=api_key)
    
    # Initialize ChromaDB client (persistent)
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    logger.info(f"Initializing ChromaDB at: {db_path}")
    
    try:
        client = chromadb.PersistentClient(path=db_path)
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        logger.error("Try deleting the 'chroma_db' folder and running ingest again.")
        return False
        
    # Get or create collection
    collection_name = "gov_schemes"
    try:
        collection = client.get_or_create_collection(name=collection_name)
        logger.info(f"Connected to collection: {collection_name}")
    except Exception as e:
        logger.error(f"Failed to get/create collection: {e}")
        return False

    # Find scheme text files
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    if not os.path.exists(data_dir):
        logger.error(f"Data directory not found at {data_dir}")
        return False
        
    files = glob.glob(os.path.join(data_dir, "*.txt"))
    if not files:
        logger.warning(f"No .txt files found in {data_dir}")
        return False
        
    logger.info(f"Found {len(files)} scheme files to ingest.")

    total_chunks = 0
    for file_path in files:
        filename = os.path.basename(file_path)
        logger.info(f"Processing scheme file: {filename}...")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                
            # Smart chunking (approx 1500 chars per chunk with 200 overlap)
            # This ensures context isn't lost across sections
            chunk_size = 1500
            overlap = 200
            chunks = []
            
            # Use a simple but effective overlapping chunker
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                # If not at the end, try to break at a newline
                if end < len(text):
                    last_newline = text.rfind('\n', start, end)
                    if last_newline != -1 and last_newline > start + (chunk_size // 2):
                        end = last_newline + 1
                
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append(chunk_text)
                start = end - overlap
                
            logger.info(f"  Split into {len(chunks)} chunks. Generating embeddings...")
            
            for i, chunk in enumerate(chunks):
                # Generate embedding using Gemini
                doc_id = f"{filename}_chunk_{i}"
                
                try:
                    result = client.models.embed_content(
                        model="text-embedding-004",
                        contents=chunk,
                        config=types.EmbedContentConfig(task_type="retrieval_document"),
                    )
                    
                    # Upsert to Chroma
                    collection.upsert(
                        documents=[chunk],
                        metadatas=[{"source": filename, "chunk": i}],
                        ids=[doc_id],
                        embeddings=[result.embeddings[0].values]
                    )
                except Exception as e:
                    logger.error(f"  Failed to embed chunk {i}: {e}")
                    
            logger.info(f"  Successfully ingested {len(chunks)} chunks for {filename}.")
            total_chunks += len(chunks)
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")

    logger.info("==================================================")
    logger.info(f"✅ Database ingestion complete! Total chunks: {total_chunks}")
    logger.info("ChromaDB is now ready for GovGPT RAG queries.")
    logger.info("==================================================")
    return True

if __name__ == "__main__":
    ingest_data()
