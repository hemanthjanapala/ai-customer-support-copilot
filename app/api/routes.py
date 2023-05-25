import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.records import ModelCallRecord
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationHistory,
    HealthResponse,
    MetricsResponse,
)
from app.observability import hash_customer_id
from app.repositories.db import check_database
from app.services.conversation_service import conversation_service
from app.services.intent_service import classify_intent, classify_intent_llm
from app.services.llm_service import llm_service
from app.services.response_service import generate_response, generate_response_llm

router = APIRouter()
logger = logging.getLogger("copilot.chat")

# Phase 1 in-memory operational state. Phase 2: shared stores.
_idempotency: dict[str, dict] = {}
_rate_buckets: dict[str, list[float]] = defaultdict(list)
_latencies: list[float] = []
_error_count = 0
_request_count = 0
_llm_calls = 0
_llm_errors = 0
_prompt_tokens = 0
_completion_tokens = 0


def _check_rate_limit(customer_id: str) -> None:
    now = time.time()
    bucket = _rate_buckets[customer_id]
    cutoff = now - 60
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")
    bucket.append(now)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(int(pct / 100 * len(ordered)), len(ordered) - 1)
    return ordered[idx]


def _record_from_result(stage: str, result, request_id: str, idempotency_key: str | None) -> ModelCallRecord:
    return ModelCallRecord(
        stage=stage,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_ms=result.latency_ms,
        status=result.status,
        request_id=request_id,
        idempotency_key=idempotency_key,
    )


def _error_record(stage: str, request_id: str, idempotency_key: str | None) -> ModelCallRecord:
    return ModelCallRecord(
        stage=stage,
        model=settings.openai_model,
        prompt_tokens=0,
        completion_tokens=0,
        latency_ms=0,
        status="error",
        request_id=request_id,
        idempotency_key=idempotency_key,
    )


def _log_model_call(
    conversation_id: str | None,
    record: ModelCallRecord,
    request_id: str,
    customer_id: str,
    intent: str | None = None,
) -> None:
    """Persist the model call, update metrics counters, and emit a JSON log line."""
    global _llm_calls, _llm_errors, _prompt_tokens, _completion_tokens
    conversation_service.log_model_call(conversation_id, record)
    _llm_calls += 1
    if record.status != "ok":
        _llm_errors += 1
    _prompt_tokens += record.prompt_tokens or 0
    _completion_tokens += record.completion_tokens or 0
    logger.info(
        f"llm {record.stage} {record.status}",
        extra={
            "request_id": request_id,
            "customer_id": hash_customer_id(customer_id),
            "stage": record.stage,
            "model": record.model,
            "intent": intent,
            "latency_ms": record.latency_ms,
            "prompt_tokens": record.prompt_tokens,
            "completion_tokens": record.completion_tokens,
            "status": record.status,
        },
    )


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    request: Request,
    x_idempotency_key: str | None = Header(default=None),
):
    global _error_count, _request_count
    start = time.time()
    _request_count += 1
    request_id = request.state.request_id

    if x_idempotency_key and x_idempotency_key in _idempotency:
        cached = _idempotency[x_idempotency_key]
        return JSONResponse(content={**cached, "request_id": request_id})

    _check_rate_limit(body.customer_id)

    message = body.message.strip()
    if not message:
        _error_count += 1
        raise HTTPException(status_code=422, detail="Message must not be blank.")

    use_llm = llm_service.is_configured()
    conversation_id = conversation_service.get_or_create(body.conversation_id, body.customer_id)

    # --- Intent stage ---
    if use_llm:
        try:
            intent, intent_result = classify_intent_llm(message, llm_service)
            _log_model_call(
                conversation_id,
                _record_from_result("intent", intent_result, request_id, x_idempotency_key),
                request_id,
                body.customer_id,
                intent=intent,
            )
        except Exception:
            # Degrade gracefully: a failed intent call must not fail the request.
            _log_model_call(
                conversation_id,
                _error_record("intent", request_id, x_idempotency_key),
                request_id,
                body.customer_id,
            )
            intent = "GENERAL_SUPPORT"
    else:
        intent = classify_intent(message)

    # --- Response stage ---
    try:
        if use_llm:
            history = conversation_service.history(conversation_id)
            reply, response_result = generate_response_llm(intent, history, message, llm_service)
            _log_model_call(
                conversation_id,
                _record_from_result("response", response_result, request_id, x_idempotency_key),
                request_id,
                body.customer_id,
                intent=intent,
            )
        else:
            reply = generate_response(intent, message)
    except Exception:
        _error_count += 1
        if use_llm:
            _log_model_call(
                conversation_id,
                _error_record("response", request_id, x_idempotency_key),
                request_id,
                body.customer_id,
                intent=intent,
            )
        # Keep the user's message so the conversation isn't lost.
        conversation_service.add_message(conversation_id, "user", message, intent)
        raise HTTPException(
            status_code=502,
            detail="Support service is temporarily unavailable. Please try again.",
        )

    conversation_service.save_exchange(conversation_id, message, reply, intent)

    latency_ms = (time.time() - start) * 1000
    _latencies.append(latency_ms)
    logger.info(
        "chat completed",
        extra={
            "request_id": request_id,
            "customer_id": hash_customer_id(body.customer_id),
            "intent": intent,
            "latency_ms": int(latency_ms),
            "status": "ok",
        },
    )

    payload = {
        "conversation_id": conversation_id,
        "intent": intent,
        "response": reply,
        "request_id": request_id,
    }
    if x_idempotency_key:
        _idempotency[x_idempotency_key] = {k: v for k, v in payload.items() if k != "request_id"}
    return payload


@router.get("/conversations/{conversation_id}", response_model=ConversationHistory)
def get_conversation(conversation_id: str):
    messages = conversation_service.all_messages(conversation_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return ConversationHistory(
        conversation_id=conversation_id,
        customer_id=conversation_service.customer_of(conversation_id) or "",
        messages=messages,
    )


@router.get("/health", response_model=HealthResponse)
def health():
    llm = "configured" if llm_service.is_configured() else "not_configured"
    return HealthResponse(
        status="ok", database=check_database(), llm=llm, version=settings.version
    )


@router.get("/metrics", response_model=MetricsResponse)
def metrics():
    error_rate = (_error_count / _request_count) if _request_count else 0.0
    return MetricsResponse(
        total_requests=_request_count,
        error_rate=round(error_rate, 4),
        latency_p50_ms=round(_percentile(_latencies, 50), 1),
        latency_p95_ms=round(_percentile(_latencies, 95), 1),
        llm_total_calls=_llm_calls,
        llm_error_count=_llm_errors,
        total_prompt_tokens=_prompt_tokens,
        total_completion_tokens=_completion_tokens,
    )
