"""
WebSocket chat handler.

BUG FIXES:
  16. thread_id was hardcoded to "global_support_session" — ALL users shared the same
      LangGraph memory checkpoint, meaning conversation history from user A leaked into
      user B's session. Fix: generate a UUID per connection.
  17. conversation_history was missing from the initial state dict, so the first call
      always started with an empty history even when the MemorySaver had previous data.
      Now we seed from the graph checkpoint when available.
  18. Exceptions during graph.ainvoke were not caught — a single Groq timeout would
      crash the WebSocket loop, dropping the client silently. Fix: wrap in try/except
      and send a JSON error frame so the frontend can display a friendly message.
  19. The client had no way to distinguish an AI message from a system error.
      Fix: send JSON frames with { type, text } so the frontend can react correctly.
"""
import json
import logging
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from app.graph.workflow import app_graph

logger = logging.getLogger(__name__)


async def websocket_handler(websocket: WebSocket) -> None:
    await websocket.accept()

    # One unique thread per browser connection → isolated memory checkpoints
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    logger.info("WebSocket connected — thread_id=%s", thread_id)

    async def send(msg_type: str, text: str) -> None:
        await websocket.send_text(json.dumps({"type": msg_type, "text": text}))

    try:
        while True:
            raw = await websocket.receive_text()
            user_message = raw.strip()
            if not user_message:
                continue

            # Retrieve existing checkpoint state to carry conversation_history forward
            saved = app_graph.get_state(config)
            history = []
            if saved and saved.values:
                history = saved.values.get("conversation_history", [])

            state = {
                "user_message": user_message,
                "intent": "",
                "order_id": None,
                "sentiment": "",
                "kb_results": [],
                "action_result": "",
                "escalation_needed": False,
                "final_response": "",
                "conversation_history": history,
                "error": None,
            }

            try:
                result = await app_graph.ainvoke(state, config=config)
                await send("ai", result["final_response"])
            except Exception as exc:
                logger.exception("Graph invocation error for thread %s: %s", thread_id, exc)
                await send(
                    "error",
                    "I'm experiencing a technical issue. Please try again in a moment.",
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected — thread_id=%s", thread_id)
    except Exception as exc:
        logger.exception("Unexpected WebSocket error: %s", exc)
