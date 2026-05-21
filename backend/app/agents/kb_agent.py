import logging
from app.rag.chroma_client import get_collection
from app.rag.embeddings import generate_embedding

logger = logging.getLogger(__name__)

# BUG FIX 5: The original imported `collection` as a module-level global at import time.
# If ChromaDB is not yet initialised (race condition at startup) or the collection is
# empty, every subsequent query silently returns [] — no error surfaced.
# Fix: Use a lazy getter function so the collection is fetched at call time, with
# explicit exception handling that logs rather than swallows the error.

def search_knowledge_base(query: str, n_results: int = 3) -> list[str]:
    """
    Embeds `query` and returns the top-n matching document strings from ChromaDB.
    Returns an empty list if the KB is empty or unavailable.
    """
    try:
        collection = get_collection()
        embedding = generate_embedding(query)
        results = collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
        )
        docs = results.get("documents", [[]])[0]
        if not docs:
            logger.warning("KB query returned no results for: %r", query[:80])
        return docs
    except Exception as exc:
        logger.error("KB search failed: %s", exc)
        return []
