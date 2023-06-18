"""Tests for Phase 3 observability: JSON log format, PII hashing, metrics."""

import json
import logging

from fastapi.testclient import TestClient

from app.main import app
from app.observability import JsonFormatter, hash_customer_id

client = TestClient(app)


def test_hash_customer_id_is_deterministic_and_not_reversible():
    h1 = hash_customer_id("C10291")
    h2 = hash_customer_id("C10291")
    assert h1 == h2
    assert len(h1) == 12
    assert "C10291" not in h1
    assert hash_customer_id("C99999") != h1


def test_json_formatter_emits_parseable_json_with_extra_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="copilot.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-abc"
    record.stage = "intent"
    parsed = json.loads(formatter.format(record))
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "hello"
    assert parsed["request_id"] == "req-abc"
    assert parsed["stage"] == "intent"
    assert "timestamp" in parsed


def test_metrics_includes_llm_and_token_fields():
    r = client.get("/api/v1/metrics")
    assert r.status_code == 200
    body = r.json()
    for field in (
        "total_requests",
        "error_rate",
        "latency_p50_ms",
        "latency_p95_ms",
        "llm_total_calls",
        "llm_error_count",
        "total_prompt_tokens",
        "total_completion_tokens",
    ):
        assert field in body, f"missing metrics field: {field}"
