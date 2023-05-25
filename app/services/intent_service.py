"""Intent classification.

Phase 1: deterministic keyword mock so the API is testable without an LLM key.
Phase 2: real LLM call using app/prompts/intent.txt, temperature 0.0,
strict label parsing, fallback to GENERAL_SUPPORT on parse failure.
"""

from pathlib import Path

from app.models.schemas import INTENTS

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ORDER_STATUS": ("where is my order", "order status", "track my order", "tracking"),
    "DELIVERY_DELAY": ("late", "delayed", "hasn't arrived", "not arrived", "supposed to arrive"),
    "REFUND": ("refund", "money back", "return"),
    "PAYMENT_PROBLEM": ("charged twice", "double charge", "payment failed", "card declined", "billing"),
    "CANCEL_ORDER": ("cancel my order", "cancel order"),
    "PRODUCT_INFORMATION": ("specs", "specification", "features"),
}


def classify_intent(message: str) -> str:
    """Phase 1 mock. Used when no LLM key is configured."""
    text = message.lower()
    for intent, keywords in _KEYWORDS.items():
        if any(k in text for k in keywords):
            return intent
    return "GENERAL_SUPPORT"


def classify_intent_llm(message: str, llm) -> tuple[str, "object"]:
    """Phase 2: real LLM classification. Returns (intent, LLMResult).

    Never raises for a bad label: unparseable output falls back to
    GENERAL_SUPPORT so one weird model response can't fail the request.
    Transport errors still raise and are handled by the caller.
    """
    system = (_PROMPT_DIR / "intent.txt").read_text()
    result = llm.complete(system=system, user=message, max_tokens=20, temperature=0.0)
    label = result.text.strip().upper().strip('"').strip("'")
    if label not in INTENTS:
        return "GENERAL_SUPPORT", result
    return label, result


def is_valid_intent(label: str) -> bool:
    return label in INTENTS
