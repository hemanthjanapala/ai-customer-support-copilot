from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_chat_creates_conversation():
    r = client.post(
        "/api/v1/chat",
        json={"customer_id": "C1", "message": "I was charged twice for my order."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "PAYMENT_PROBLEM"
    assert body["conversation_id"]
    assert "x-request-id" in r.headers


def test_chat_validation_rejects_blank():
    r = client.post("/api/v1/chat", json={"customer_id": "C1", "message": "   "})
    assert r.status_code == 422


def test_conversation_history():
    r = client.post(
        "/api/v1/chat", json={"customer_id": "C2", "message": "Where is my order?"}
    )
    conv = r.json()["conversation_id"]
    r2 = client.get(f"/api/v1/conversations/{conv}")
    assert r2.status_code == 200
    assert len(r2.json()["messages"]) == 2


def test_conversation_not_found():
    r = client.get("/api/v1/conversations/conv-nope")
    assert r.status_code == 404


def test_idempotency_key():
    headers = {"X-Idempotency-Key": "key-123"}
    p1 = client.post(
        "/api/v1/chat",
        json={"customer_id": "C3", "message": "I want a refund."},
        headers=headers,
    ).json()
    p2 = client.post(
        "/api/v1/chat",
        json={"customer_id": "C3", "message": "I want a refund."},
        headers=headers,
    ).json()
    assert p1["conversation_id"] == p2["conversation_id"]
    assert p1["response"] == p2["response"]
