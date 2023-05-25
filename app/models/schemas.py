from typing import Literal, Optional
from pydantic import BaseModel, Field

IntentLabel = Literal[
    "ORDER_STATUS",
    "DELIVERY_DELAY",
    "REFUND",
    "PAYMENT_PROBLEM",
    "CANCEL_ORDER",
    "PRODUCT_INFORMATION",
    "GENERAL_SUPPORT",
]

INTENTS: tuple[str, ...] = (
    "ORDER_STATUS",
    "DELIVERY_DELAY",
    "REFUND",
    "PAYMENT_PROBLEM",
    "CANCEL_ORDER",
    "PRODUCT_INFORMATION",
    "GENERAL_SUPPORT",
)


class ChatRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: Optional[str] = Field(default=None, min_length=1, max_length=64)


class ChatResponse(BaseModel):
    conversation_id: str
    intent: str
    response: str
    request_id: str


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    intent: Optional[str] = None
    created_at: str


class ConversationHistory(BaseModel):
    conversation_id: str
    customer_id: str
    messages: list[Message]


class HealthResponse(BaseModel):
    status: str
    database: str
    llm: str
    version: str


class MetricsResponse(BaseModel):
    total_requests: int
    error_rate: float
    latency_p50_ms: float
    latency_p95_ms: float
    llm_total_calls: int
    llm_error_count: int
    total_prompt_tokens: int
    total_completion_tokens: int
