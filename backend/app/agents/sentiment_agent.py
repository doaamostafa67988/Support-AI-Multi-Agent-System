import logging
from groq import Groq
from app.config import GROQ_API_KEY

logger = logging.getLogger(__name__)

_client = Groq(api_key=GROQ_API_KEY)

def analyze_sentiment(message: str) -> str:
    """
    Returns 'negative' ONLY for explicitly angry/abusive messages.
    Neutral requests like 'I need help' or 'I have an issue' are 'positive'.
    """
    prompt = (
        "You are a customer support sentiment classifier.\n"
        "Classify the message below as 'negative' ONLY if it contains EXPLICIT anger, "
        "insults, threats, or strong frustration (e.g. 'this is terrible', 'I am furious', "
        "'worst service ever', 'you are useless').\n"
        "Neutral help requests like 'I need help', 'I have an issue with my order', "
        "'my package hasn't arrived' are NOT negative — label those 'positive'.\n"
        "When in doubt, choose 'positive'.\n"
        "Reply ONLY with the single word: negative OR positive. No other text.\n\n"
        f"Message: \"{message}\""
    )
    try:
        response = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=5,
        )
        label = response.choices[0].message.content.strip().lower()
        return "negative" if "negative" in label else "positive"
    except Exception as exc:
        logger.warning("Sentiment analysis failed, defaulting to positive: %s", exc)
        return "positive"
