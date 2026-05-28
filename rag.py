import os
import logging
import re
from collections import Counter
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


def extract_keywords(query: str) -> list[str]:
    """Extract important keywords from query for hybrid search."""
    # Common scheme-related keywords in Hindi and English
    scheme_keywords = {
        'pm kisan', 'kisan', 'farmer', 'agriculture', 'crop',
        'mgnrega', 'job card', 'employment', 'wage', 'rural',
        'ayushman', 'health', 'hospital', 'medicine', 'pm-jay',
        'ration', 'pds', 'food', 'grain', 'fps', 'fair price',
        'pension', 'nsap', 'old age', 'widow', 'social assistance',
        'awas', 'housing', 'house', 'pmay', 'shelter',
        'ujjwala', 'gas', 'lpg', 'cooking', 'connection',
        'scholarship', 'education', 'student', 'nsp',
        'passport', 'visa', 'travel',
        'railway', 'train', 'ticket', 'refund',
        'bank', 'loan', 'mudra', 'account',
        'electricity', 'power', 'bijli', 'meter',
        'road', 'pwd', 'highway', 'construction',
        'water', 'jal', 'pipeline', 'drinking',
        'certificate', 'birth', 'death', 'caste',
        'police', 'fir', 'complaint',
        'land', 'property', 'registry', 'record',
        'aadhar', 'uidai', 'biometric',
        'epfo', 'pf', 'provident fund'
    }
    
    # Convert to lowercase and split
    words = re.findall(r'\b\w+\b', query.lower())
    
    # Filter for scheme-related keywords and meaningful words (length > 2)
    keywords = [w for w in words if w in scheme_keywords or len(w) > 3]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for word in keywords:
        if word not in seen:
            seen.add(word)
            unique_keywords.append(word)
    
    return unique_keywords[:10]  # Limit to top 10 keywords


def expand_query(query: str) -> str:
    """Expand query with synonyms and related terms for better retrieval."""
    expansions = {
        'kisan': 'farmer agriculture crop',
        'ration': 'pds food grain fair price shop fps',
        'pension': 'old age widow social assistance nsap',
        'health': 'hospital medicine ayushman pm-jay treatment',
        'housing': 'awas house shelter pmay',
        'employment': 'job wage work mgnrega rural',
        'gas': 'lpg ujjwala cooking fuel',
        'education': 'scholarship student school nsp',
        'bijli': 'electricity power meter',
    }
    
    query_lower = query.lower()
    expanded_terms = []
    
    for word in query_lower.split():
        if word in expansions:
            expanded_terms.append(expansions[word])
    
    if expanded_terms:
        return query + ' ' + ' '.join(expanded_terms)
    return query


def get_scheme_context(query: str, n_results: int = 3) -> str:
    """
    Takes the citizen's problem description (query), generates an embedding,
    and searches the local ChromaDB for the most relevant scheme rules.
    Uses hybrid search (semantic + keyword) for better retrieval.
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
        gemini_client = genai.Client(api_key=api_key)
        
        # Expand query for better retrieval
        expanded_query = expand_query(query)
        
        embed_result = gemini_client.models.embed_content(
            model="text-embedding-004",
            contents=expanded_query,
            config=types.EmbedContentConfig(task_type="retrieval_query"),
        )

        query_embedding = embed_result.embeddings[0].values

        # Query ChromaDB using the correctly scoped chroma_client / collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        if not results['documents'] or not results['documents'][0]:
            # Fallback: try keyword-based search if semantic search fails
            keywords = extract_keywords(query)
            logger.info(f"Semantic search failed, trying keyword search with: {keywords}")
            
            if keywords:
                # Try searching with each keyword
                for keyword in keywords[:3]:
                    keyword_embed = gemini_client.models.embed_content(
                        model="text-embedding-004",
                        contents=keyword,
                        config=types.EmbedContentConfig(task_type="retrieval_query"),
                    )
                    keyword_results = collection.query(
                        query_embeddings=[keyword_embed.embeddings[0].values],
                        n_results=2
                    )
                    if keyword_results['documents'] and keyword_results['documents'][0]:
                        if not results['documents']:
                            results = keyword_results
                        else:
                            results['documents'][0].extend(keyword_results['documents'][0])
                            results['metadatas'][0].extend(keyword_results['metadatas'][0])
            
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