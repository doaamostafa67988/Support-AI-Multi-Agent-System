import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.websocket.chat_socket import websocket_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    BUG FIX 20: FastAPI startup/shutdown events were missing entirely.
    The lifespan context manager warms up expensive singletons (embedding model,
    ChromaDB client) at startup so the first user request is not slow.
    """
    logger.info("🚀 Starting Support AI backend…")
    # Warm up embedding model and ChromaDB connection at startup
    from app.rag.embeddings import generate_embedding
    from app.rag.chroma_client import get_collection
    try:
        get_collection()
        generate_embedding("warmup")
        logger.info("✅ ChromaDB and embedding model ready.")
    except Exception as exc:
        logger.warning("Startup warmup failed (non-fatal): %s", exc)
    yield
    logger.info("👋 Shutting down Support AI backend.")


app = FastAPI(
    title="Multi-Agent Customer Support API",
    version="2.0.0",
    description="LangGraph-orchestrated customer support system with RAG and Groq.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Tighten this in production to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket_handler(websocket)


@app.get("/", tags=["Health"])
def health():
    return {"status": "healthy", "service": "Support AI Engine", "version": "2.0.0"}


@app.get("/health", tags=["Health"])
def health_detailed():
    from app.rag.chroma_client import get_collection
    try:
        col = get_collection()
        count = col.count()
        kb_status = f"ok ({count} documents)"
    except Exception as exc:
        kb_status = f"error: {exc}"

    return {
        "status": "healthy",
        "chromadb": kb_status,
    }
# HF Trigger Sync Comment