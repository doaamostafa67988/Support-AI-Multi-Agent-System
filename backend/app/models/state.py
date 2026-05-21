from typing import TypedDict, List, Any, Optional


class SupportState(TypedDict):
    user_message: str
    intent: str                      # "refund" | "tracking" | "return" | "complaint" | "general"
    order_id: Optional[str]
    sentiment: str                   # "positive" | "negative"
    kb_results: List[str]
    action_result: str
    escalation_needed: bool
    final_response: str
    conversation_history: List[dict]  # FIX: tracks multi-turn context for LLM calls
    error: Optional[str]              # FIX: surface errors instead of silently swallowing them
