import logging
from typing import Optional
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# BUG FIX 10: SentenceTransformer was instantiated at module import time, meaning
# the 80 MB model was downloaded/loaded before the FastAPI app even started.
# Fix: lazy-load on first call so startup is instant.

_model: Optional[SentenceTransformer] = None
MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def generate_embedding(text: str) -> list[float]:
    """Encode text and return a flat list of floats suitable for ChromaDB."""
    try:
        return _get_model().encode(text, convert_to_numpy=True).tolist()
    except Exception as exc:
        logger.error("Embedding generation failed: %s", exc)
        raise
