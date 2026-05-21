"""
Run once to populate ChromaDB with seed knowledge base documents.
Usage (from backend/ directory):
    python -m app.rag.ingest
"""
import logging
from app.rag.chroma_client import get_collection
from app.rag.embeddings import generate_embedding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAMPLE_DOCS = [
    "Customers can return products within 14 days of purchase for a full refund.",
    "Refunds are processed back to the original payment method within 5 business days after the return is received.",
    "Orders can be tracked from your account dashboard under the 'Orders' section.",
    "To initiate a return, log in to your account, go to Order History, and click 'Return Item'.",
    "Damaged or defective items are eligible for immediate replacement or refund with no return required.",
    "Our customer support team is available Monday through Friday, 9 AM to 6 PM EST.",
    "Gift orders can be returned by the recipient. Refunds go to the original purchaser's payment method.",
    "Subscription orders can be cancelled at any time. Cancellation takes effect at the end of the billing period.",
]


def ingest_documents(documents: list[str], overwrite: bool = False) -> None:
    """
    BUG FIX 11: Original ingest didn't check for duplicates — re-running it doubled
    every document in the collection. Fix: use ChromaDB upsert with stable IDs so
    re-ingestion is idempotent.
    """
    collection = get_collection()

    if overwrite:
        existing = collection.get()
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            logger.info("Cleared %d existing documents.", len(existing["ids"]))

    ids = [f"doc_{i}" for i in range(len(documents))]
    embeddings = [generate_embedding(doc) for doc in documents]

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
    )
    logger.info("✅ %d documents upserted into ChromaDB collection 'support_docs'.", len(documents))


if __name__ == "__main__":
    ingest_documents(SAMPLE_DOCS, overwrite=True)
