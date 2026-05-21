import json
import logging
from typing import Optional
from groq import Groq
from app.config import GROQ_API_KEY

logger = logging.getLogger(__name__)
client = Groq(api_key=GROQ_API_KEY)

# BUG FIX 1: The original code mapped intents to "action"/"kb" strings but the graph
# routed based on "refund"/"tracking"/"return" etc. This mismatch caused the
# action_agent to never be triggered. Now we keep the raw LLM intent and let the
# graph's route_after_analysis function do the routing logic.

def analyze_user_intent(message: str, history: Optional[list] = None) -> dict:
    """
    Classifies user intent and extracts order_id using Groq/Llama.
    Returns dict with keys: intent (str), order_id (str | None).
    """
    system_prompt = (
        "You are a customer support intent classifier. "
        "Respond ONLY with a valid JSON object. No markdown, no extra text. "
        'Keys: "intent" (one of: refund, tracking, return, complaint, general), '
        '"order_id" (alphanumeric string or null).'
    )

    # BUG FIX 2: Include conversation history so the model has multi-turn context
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history[-6:])  # last 3 turns to keep prompt short
    messages.append({"role": "user", "content": f'Message: "{message}"'})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,   # BUG FIX 3: low temp for deterministic classification
            max_tokens=128,
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)

        intent = data.get("intent", "general")
        if intent not in {"refund", "tracking", "return", "complaint", "general"}:
            intent = "general"

        order_id = data.get("order_id")
        if order_id is not None:
            order_id = str(order_id).strip() or None

        return {"intent": intent, "order_id": order_id}

    except json.JSONDecodeError as exc:
        logger.warning("Intent JSON decode error: %s", exc)
        return {"intent": "general", "order_id": None}
    except Exception as exc:
        logger.error("Intent analysis failed: %s", exc)
        return {"intent": "general", "order_id": None}
