"""Shared record types for model-call observability."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelCallRecord:
    stage: str  # intent | response
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    status: str  # ok | timeout | error | fallback
    request_id: str
    idempotency_key: Optional[str] = None
