import json
import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

# BUG FIX 8: The original used a blocking `open(..., "a")` inside an async graph node.
# Blocking I/O inside an async event loop stalls the entire server.
# Fix: offload the write to a thread via asyncio.to_thread.

RESOLVED_PATH = Path("resolved_cases.json")


def _sync_write(data: dict) -> None:
    """Blocking write — called from a worker thread via asyncio.to_thread."""
    with RESOLVED_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False) + "\n")


async def save_resolution(data: dict) -> None:
    """Non-blocking resolution logger."""
    try:
        await asyncio.to_thread(_sync_write, data)
    except Exception as exc:
        logger.warning("Failed to persist resolution log: %s", exc)
