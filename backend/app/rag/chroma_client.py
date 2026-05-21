import chromadb
from pathlib import Path
from typing import Optional

# BUG FIX 9: The original created the ChromaDB client AND fetched the collection at
# module import time with no error handling. If the path doesn't exist on the first
# import, the whole app crashes at startup.
# Fix: expose a lazy get_collection() function called at runtime.

_client: Optional[chromadb.PersistentClient] = None
_collection = None

CHROMA_PATH = str(Path(__file__).parent.parent.parent / "chroma_db")
COLLECTION_NAME = "support_docs"


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def get_collection():
    global _collection
    if _collection is None:
        _collection = get_client().get_or_create_collection(COLLECTION_NAME)
    return _collection
