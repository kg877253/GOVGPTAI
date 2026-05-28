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
client = None
collection = None

if _packages_ready:
    # Check if DB directory exists and is not empty
    if os.path.exists(db_path) and os.listdir(db_path):
        try:
            client = chromadb.PersistentClient(path=db_path)
            collection = client.get_collection(name="gov_schemes")
            logger.info("ChromaDB connected and 'gov_schemes' collection loaded.")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            client = None
    else:
        logger.warning(f"ChromaDB directory '{db_path}' not found or empty. Run ingest.py first.")

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
        # Generate embedding for the query
        client = genai.Client(api_key=api_key)
        embed_result = client.models.embed_content(
            model="text-embedding-004",
            contents=query,
            config=types.EmbedContentConfig(task_type="retrieval_query"),
        )
        query_embedding = embed_result.embeddings[0].values

        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        if not results['documents'] or not results['documents'][0]:
            return "No matching scheme context found in database."

        # Concatenate retrieved chunks
        context_chunks = results['documents'][0]
        sources = [meta.get('source', 'Unknown') for meta in results['metadatas'][0]]
        
        logger.info(f"RAG matched sources: {sources}")
        
        combined_context = "\n\n--- MATCHING SCHEME RULES ---\n\n".join(context_chunks)
        return combined_context

    except Exception as e:
        logger.error(f"Error during RAG query: {e}")
        return f"RAG error: {str(e)}"
