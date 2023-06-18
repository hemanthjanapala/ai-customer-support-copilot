"""Unit tests for the Postgres-backed conversation store.

Uses SQLite in-memory so no database server is needed. PostgreSQL is used
in production via docker compose; SQL is kept portable between the two.
"""

from app.models.records import ModelCallRecord
from app.repositories.postgres import PostgresConversationService


def _store() -> PostgresConversationService:
    return PostgresConversationService("sqlite:///:memory:", history_window=3)


def _record(stage: str = "intent") -> ModelCallRecord:
    return ModelCallRecord(
        stage=stage,
        model="test-model",
        prompt_tokens=10,
        completion_tokens=5,
        latency_ms=120,
        status="ok",
        request_id="req-test",
    )


def test_get_or_create_reuses_existing():
    s = _store()
    c1 = s.get_or_create(None, "C1")
    c2 = s.get_or_create(c1, "C1")
    assert c1 == c2
    assert s.customer_of(c1) == "C1"


def test_get_or_create_missing_returns_none():
    s = _store()
    assert s.all_messages("conv-nope") is None
    assert s.customer_of("conv-nope") is None


def test_save_exchange_writes_both_messages_atomically():
    s = _store()
    conv = s.get_or_create(None, "C1")
    s.save_exchange(conv, "hello", "hi there", "GENERAL_SUPPORT")
    msgs = s.all_messages(conv)
    assert msgs is not None
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert all(m.intent == "GENERAL_SUPPORT" for m in msgs)


def test_history_window_limits_results():
    s = _store()
    conv = s.get_or_create(None, "C1")
    for i in range(5):
        s.save_exchange(conv, f"q{i}", f"a{i}", "GENERAL_SUPPORT")
    assert len(s.all_messages(conv)) == 10
    assert len(s.history(conv)) == 3  # history_window=3


def test_log_model_call_persists():
    s = _store()
    conv = s.get_or_create(None, "C1")
    s.log_model_call(conv, _record("intent"))
    s.log_model_call(conv, _record("response"))
    assert len(s._model_calls if hasattr(s, "_model_calls") else []) == 0  # postgres has no in-mem list
    # Verify rows landed via a direct query through the session.
    from app.repositories.postgres import ModelRequest

    with s._Session() as session:
        rows = session.query(ModelRequest).all()
    assert len(rows) == 2
    assert {r.stage for r in rows} == {"intent", "response"}
    assert rows[0].prompt_tokens == 10
