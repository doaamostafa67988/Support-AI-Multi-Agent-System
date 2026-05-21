import logging

logger = logging.getLogger(__name__)

# BUG FIX 6: The original escalation logic escalated EVERY query where kb_results was
# empty. Since the KB has only 3 seed documents, almost any message that isn't an exact
# match returns []. This means nearly ALL conversations were immediately escalated,
# bypassing the Groq-powered response entirely.
# Fix: Only escalate on explicitly negative sentiment OR a detected complaint intent
# with no KB results. General queries with empty KB are handled gracefully by the
# responder node instead.

def should_escalate(sentiment: str, intent: str, kb_results: list) -> bool:
    """
    True → route to human agent.
    Escalation triggers:
      1. Explicit negative sentiment (angry / frustrated customer)
      2. 'complaint' intent with zero KB matches (we have nothing useful to say)
    """
    if sentiment == "negative":
        logger.info("Escalation triggered: negative sentiment")
        return True

    if intent == "complaint" and not kb_results:
        logger.info("Escalation triggered: complaint with no KB match")
        return True

    return False
