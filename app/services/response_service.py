"""Response generation.

Phase 1: templated mock responses per intent.
Phase 2: build the prompt from app/prompts/response.txt plus conversation
history and call the LLM with timeout + one retry. Output is scanned for
secret-like patterns before being returned.
"""

import re
from pathlib import Path

from app.models.schemas import Message

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{8,}"),  # api-key-like
    re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),  # card-number-like
)

_SAFE_FALLBACK = (
    "I'm having trouble generating a safe response right now. "
    "Please try again or contact support directly."
)

_RESPONSES: dict[str, str] = {
    "ORDER_STATUS": (
        "Thanks for reaching out. I can help with your order status. "
        "Could you share your order number so I can look it up?"
    ),
    "DELIVERY_DELAY": (
        "I'm sorry your delivery is delayed. Delays are often caused by carrier "
        "backlogs. Could you share your order number so I can check the latest tracking?"
    ),
    "REFUND": (
        "I can help with your refund request. Refunds are typically issued to the "
        "original payment method within 5-10 business days once approved. "
        "Could you share your order number?"
    ),
    "PAYMENT_PROBLEM": (
        "I'm sorry about the payment issue. Please check with your bank whether the "
        "extra charge is a temporary authorization hold. If the duplicate charge posts, "
        "share your order number and I'll escalate it."
    ),
    "CANCEL_ORDER": (
        "I can help cancel your order if it hasn't shipped yet. "
        "Could you share your order number so I can check?"
    ),
    "PRODUCT_INFORMATION": (
        "Happy to help with product questions. "
        "Could you tell me which product you're asking about?"
    ),
    "GENERAL_SUPPORT": (
        "Thanks for contacting support. "
        "Could you share a few more details so I can point you in the right direction?"
    ),
}


def generate_response(intent: str, message: str) -> str:
    """Phase 1 mock. Used when no LLM key is configured."""
    return _RESPONSES.get(intent, _RESPONSES["GENERAL_SUPPORT"])


def _scan_output(text: str) -> str:
    """Block secret-like output. Returns safe text (never the raw secret)."""
    if any(p.search(text) for p in _SECRET_PATTERNS):
        return _SAFE_FALLBACK
    return text


def generate_response_llm(
    intent: str, history: list[Message], message: str, llm
) -> tuple[str, "object"]:
    """Phase 2: real LLM response. Returns (response_text, LLMResult)."""
    template = (_PROMPT_DIR / "response.txt").read_text()
    history_text = "\n".join(f"{m.role}: {m.content}" for m in history) or "(no prior messages)"
    # .replace instead of .format: user messages may contain braces.
    user_prompt = (
        template.replace("{intent}", intent)
        .replace("{history}", history_text)
        .replace("{message}", message)
    )
    result = llm.complete(
        system="You are a helpful customer support assistant.",
        user=user_prompt,
        max_tokens=500,
        temperature=0.7,
    )
    return _scan_output(result.text), result
