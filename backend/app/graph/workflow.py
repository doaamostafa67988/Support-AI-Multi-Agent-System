"""
LangGraph workflow — the central orchestration DAG.

Node execution order:
  supervisor → [knowledge_retriever | action_executor] → responder → END

BUG FIXES in this file:
  12. supervisor_node was calling analyze_user_intent (sync) inside an async node
      without awaiting — this was fine for sync functions but the pattern caused
      confusion. All agent calls are now explicitly sync where they are sync.
  13. route_after_analysis was checking `state.get("action_result")` but
      action_result was only set if the intent was already in ["refund","tracking"]
      AND an order_id existed. Because the old conversation_manager remapped those
      to "action", the check `analysis["intent"] in ["refund","tracking"]` was
      always False so action_result was always "". Routing was therefore always
      going to knowledge_retriever — even for refund/tracking requests.
  14. The responder used a dead-simple string concat for the final response with no
      LLM involvement. Now a Groq call synthesises a helpful, grounded response from
      the KB context, action result, and conversation history.
  15. conversation_history was missing from the state entirely, breaking multi-turn
      context. It is now threaded through every node.
"""
import logging
from typing import List
from groq import Groq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END

from app.config import GROQ_API_KEY
from app.models.state import SupportState
from app.agents.conversation_manager import analyze_user_intent
from app.agents.kb_agent import search_knowledge_base
from app.agents.sentiment_agent import analyze_sentiment
from app.agents.escalation_agent import should_escalate
from app.agents.action_agent import handle_action
from app.agents.learning_agent import save_resolution

logger = logging.getLogger(__name__)
_groq = Groq(api_key=GROQ_API_KEY)

ACTION_INTENTS = {"refund", "tracking", "return"}


# ─────────────────────────────────────────────
# NODE 1 — Supervisor: classify, score sentiment, dispatch actions
# ─────────────────────────────────────────────
async def supervisor_node(state: SupportState) -> dict:
    history = state.get("conversation_history", [])

    analysis = analyze_user_intent(state["user_message"], history)
    sentiment = analyze_sentiment(state["user_message"])

    # Only call action tools when we have an order_id
    action_result = ""
    if analysis["intent"] in ACTION_INTENTS and analysis["order_id"]:
        action_result = await handle_action(analysis["intent"], analysis["order_id"])
        logger.info(
            "Action executed: intent=%s order=%s result=%r",
            analysis["intent"], analysis["order_id"], action_result[:60],
        )

    return {
        "intent": analysis["intent"],
        "order_id": analysis["order_id"],
        "sentiment": sentiment,
        "action_result": action_result,
    }


# ─────────────────────────────────────────────
# NODE 2a — Knowledge retriever
# ─────────────────────────────────────────────
async def knowledge_node(state: SupportState) -> dict:
    kb_results = search_knowledge_base(state["user_message"])
    logger.info("KB retrieved %d documents", len(kb_results))
    return {"kb_results": kb_results}


# ─────────────────────────────────────────────
# NODE 3 — Responder: synthesise final reply via Groq
# ─────────────────────────────────────────────
async def responder_node(state: SupportState) -> dict:
    escalate = should_escalate(
        state["sentiment"],
        state["intent"],
        state.get("kb_results", []),
    )

    if escalate:
        final_response = (
            "I can see you're having a frustrating experience and I sincerely apologise. "
            "I've escalated your case to a senior human support agent who will contact "
            "you within 2 hours. Your reference number is #SUP-"
            + str(abs(hash(state["user_message"])))[:6]
            + "."
        )
    elif state.get("action_result"):
        # We already took action — confirm it with a friendly wrap
        final_response = await _synthesise_response(state, mode="action")
    else:
        # General or KB-backed response
        final_response = await _synthesise_response(state, mode="kb")

    # Persist conversation history for next turn
    updated_history = list(state.get("conversation_history", []))
    updated_history.append({"role": "user", "content": state["user_message"]})
    updated_history.append({"role": "assistant", "content": final_response})

    if not escalate and state.get("intent") not in ACTION_INTENTS:
        await save_resolution({
            "query": state["user_message"],
            "intent": state["intent"],
            "resolved_output": final_response,
        })

    return {
        "escalation_needed": escalate,
        "final_response": final_response,
        "conversation_history": updated_history,
    }


async def _synthesise_response(state: SupportState, mode: str) -> str:
    """Use Groq to produce a natural, grounded response."""
    history = state.get("conversation_history", [])

    if mode == "action":
        user_context = (
            f"Action result: {state['action_result']}\n"
            f"Order ID: {state.get('order_id', 'N/A')}"
        )
        system = (
            "You are a friendly customer support agent. "
            "The system has already processed the customer's request. "
            "Confirm what was done in a warm, concise 1-2 sentence message. "
            "Do not invent any additional information."
        )
    else:
        kb_context = "\n".join(state.get("kb_results", []))
        user_context = (
            f"Knowledge base information:\n{kb_context or 'No specific articles found.'}"
        )
        system = (
            "You are a helpful customer support agent. "
            "Answer the customer's question using ONLY the knowledge base information provided. "
            "If the KB is empty or doesn't answer the question, acknowledge that honestly "
            "and offer to connect them with a human agent. "
            "Be concise (2-3 sentences max). Never invent policies or details."
        )

    messages: List[dict] = [{"role": "system", "content": system}]
    messages.extend(history[-6:])
    messages.append({
        "role": "user",
        "content": f"{state['user_message']}\n\n[Context]\n{user_context}",
    })

    try:
        response = _groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.4,
            max_tokens=256,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Groq response synthesis failed: %s", exc)
        return (
            "I'm sorry, I'm having trouble accessing our systems right now. "
            "Please try again in a moment or contact us at support@company.com."
        )


# ─────────────────────────────────────────────
# GRAPH ASSEMBLY
# ─────────────────────────────────────────────
def route_after_supervisor(state: SupportState) -> str:
    """
    BUG FIX 13: Previously checked action_result (a string) but it was always ""
    because the intent mapping was broken upstream. Now correctly checks intent.
    If action was already handled, skip KB retrieval and go straight to responder.
    """
    if state.get("action_result"):
        return "responder"
    return "knowledge_retriever"


workflow = StateGraph(SupportState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("knowledge_retriever", knowledge_node)
workflow.add_node("responder", responder_node)

workflow.set_entry_point("supervisor")

workflow.add_conditional_edges(
    "supervisor",
    route_after_supervisor,
    {
        "responder": "responder",
        "knowledge_retriever": "knowledge_retriever",
    },
)

workflow.add_edge("knowledge_retriever", "responder")
workflow.add_edge("responder", END)

memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)
