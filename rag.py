import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("GovGPT-RAG")

# Try to import required packages
try:
    import chromadb
    from google import genai
    from google.genai import types
    _packages_ready = True
except ImportError:
    _packages_ready = False
    logger.error("Required packages (chromadb, google-genai) are missing.")

# Initialize ChromaDB persistent client
db_path = os.path.join(os.path.dirname(__file__), "chroma_db")

# BUG FIX #1 (rag.py): Renamed ChromaDB client variable from `client` to
# `chroma_client` so it does NOT collide with the `genai.Client` instance
# created later inside get_scheme_context(). The original code overwrote the
# ChromaDB client reference, making embed_content() crash with AttributeError.

chroma_client = None
collection = None

if _packages_ready:
    # BUG FIX #2 (rag.py): Only connect if DB directory exists AND is non-empty.
    # If the DB doesn't exist yet, warn and defer — don't crash at import time.
    # This fixes the "crash on cold start" issue when chroma_db hasn't been
    # populated yet (i.e., ingest.py has not been run).
    if os.path.exists(db_path) and os.listdir(db_path):
        try:
            chroma_client = chromadb.PersistentClient(path=db_path)
            collection = chroma_client.get_collection(name="gov_schemes")
            logger.info("ChromaDB connected and 'gov_schemes' collection loaded.")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            chroma_client = None
            collection = None
    else:
        logger.warning(
            f"ChromaDB directory '{db_path}' not found or empty. "
            "Run ingest.py first. RAG will be disabled until then."
        )


def get_scheme_context(query: str, n_results: int = 2) -> str:
    """
    Takes the citizen's problem description (query), generates an embedding,
    and searches the local ChromaDB for the most relevant scheme rules.
    Returns the concatenated text of the top matches.
    """
    if not _packages_ready or collection is None:
        return "System running without RAG. Proceed with general knowledge."

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.startswith("YOUR_"):
        logger.error("GEMINI_API_KEY is missing or invalid.")
        return "RAG disabled due to missing API key."

    try:
        # BUG FIX #3 (rag.py): Use a LOCAL variable `gemini_client` for the
        # genai.Client instance — do NOT shadow the module-level `chroma_client`.
        # The original bug used `client = genai.Client(...)` which overwrote the
        # ChromaDB client, then called collection.query() on a dead reference.
        gemini_client = genai.Client(api_key=api_key)

        embed_result = gemini_client.models.embed_content(
            model="text-embedding-004",
            contents=query,
            config=types.EmbedContentConfig(task_type="retrieval_query"),
        )

        query_embedding = embed_result.embeddings[0].values

        # Query ChromaDB using the correctly scoped chroma_client / collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        if not results['documents'] or not results['documents'][0]:
            return "No matching scheme context found in database."

        context_chunks = results['documents'][0]
        sources = [meta.get('source', 'Unknown') for meta in results['metadatas'][0]]
        logger.info(f"RAG matched sources: {sources}")

        combined_context = "\n\n--- MATCHING SCHEME RULES ---\n\n".join(context_chunks)
        return combined_context

    except Exception as e:
        logger.error(f"Error during RAG query: {e}")
        return f"RAG error: {str(e)}"