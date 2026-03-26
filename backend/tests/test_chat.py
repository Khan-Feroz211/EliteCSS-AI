import asyncio

from fastapi.testclient import TestClient

from app.db.database import init_db
from app.main import create_app

app = create_app()
client = TestClient(app)


def _payload(model: str, content: str = "Tell me about Pakistan Affairs") -> dict:
    return {
        "model": model,
        "messages": [
            {"role": "user", "content": content},
        ],
    }


def test_chat_gpt_route(monkeypatch):
    from app.routers import chat

    monkeypatch.setattr(chat, "call_gpt", lambda messages, system_prompt=None: ("gpt ok", 11))

    res = client.post("/api/v1/chat", json=_payload("gpt"), headers={"x-user-id": "u1"})
    assert res.status_code == 200
    data = res.json()
    assert data["reply"] == "gpt ok"
    assert data["tokens_used"] == 11
    assert "x-message-id" in res.headers


def test_chat_claude_route(monkeypatch):
    from app.routers import chat

    monkeypatch.setattr(chat, "call_claude", lambda messages, system_prompt=None: ("claude ok", 12))

    res = client.post("/api/v1/chat", json=_payload("claude"), headers={"x-user-id": "u1"})
    assert res.status_code == 200
    data = res.json()
    assert data["reply"] == "claude ok"
    assert data["tokens_used"] == 12
    assert "x-message-id" in res.headers


def test_chat_gemini_route(monkeypatch):
    from app.routers import chat

    monkeypatch.setattr(chat, "call_gemini", lambda messages, system_prompt=None: ("gemini ok", 13))

    res = client.post("/api/v1/chat", json=_payload("gemini"), headers={"x-user-id": "u1"})
    assert res.status_code == 200
    data = res.json()
    assert data["reply"] == "gemini ok"
    assert data["tokens_used"] == 13
    assert "x-message-id" in res.headers


def test_validation_message_too_long():
    too_long = "x" * 2001
    res = client.post("/api/v1/chat", json=_payload("gpt", too_long), headers={"x-user-id": "u1"})
    assert res.status_code == 422


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "models_available" in data


def test_feedback_store(monkeypatch):
    from app.routers import chat

    asyncio.run(init_db())
    monkeypatch.setattr(chat, "call_gpt", lambda messages, system_prompt=None: ("gpt ok", 11))

    chat_res = client.post("/api/v1/chat", json=_payload("gpt"), headers={"x-user-id": "u1", "x-session-id": "s1"})
    assert chat_res.status_code == 200
    message_id = chat_res.headers.get("x-message-id")
    assert message_id

    feedback_res = client.post(
        "/api/v1/feedback",
        json={"message_id": message_id, "rating": 5, "comment": "helpful"},
        headers={"x-user-id": "u1", "x-session-id": "s1"},
    )
    assert feedback_res.status_code == 200
    payload = feedback_res.json()
    assert payload["status"] == "stored"
    assert isinstance(payload["feedback_id"], int)
