import logging
from typing import Optional
from app.tools.refund_tool import process_refund
from app.tools.tracking_tool import track_order

logger = logging.getLogger(__name__)

# BUG FIX 7: The original action_agent was called inside supervisor_node with the
# *original* raw LLM intents ("refund", "tracking") but the conversation_manager was
# remapping them to "action"/"kb" before returning. So the intent check in
# supervisor_node (`analysis["intent"] in ["refund", "tracking"]`) was always False
# and handle_action was never called.
# Fix: conversation_manager now returns raw intents; action dispatching is clean here.

ACTION_INTENTS = {"refund", "tracking", "return"}

async def handle_action(intent: str, order_id: Optional[str]) -> str:
    """
    Dispatches to the appropriate tool based on intent.
    Returns a human-readable result string, or empty string if not applicable.
    """
    if intent not in ACTION_INTENTS or not order_id:
        return ""

    try:
        if intent == "refund":
            return await process_refund(order_id)
        if intent == "tracking":
            return await track_order(order_id)
        if intent == "return":
            return (
                f"Return request for order #{order_id} has been logged. "
                "Please ship the item back within 14 days using the prepaid label "
                "that will be emailed to you within 24 hours."
            )
    except Exception as exc:
        logger.error("Action tool failed for intent=%s order=%s: %s", intent, order_id, exc)
        return f"We encountered an issue processing your {intent} request. Our team will follow up shortly."

    return ""
