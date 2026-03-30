import asyncio
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.db.database import init_db
from app.db.models import User
from app.dependencies import get_current_user
from app.main import create_app

app = create_app()
client = TestClient(app)


def _mock_user() -> User:
    user = User()
    user.id = 1
    user.email = "test@example.com"
    user.is_active = True
    return user


def _auth_override():
    return _mock_user()


def _payload(model: str, content: str = "Tell me about Pakistan Affairs") -> dict:
    return {
        "model": model,
        "messages": [
            {"role": "user", "content": content},
        ],
    }


def test_chat_gpt_route(monkeypatch):
    from app.routers import chat

    app.dependency_overrides[get_current_user] = _auth_override
    monkeypatch.setattr(
        chat, "call_gpt", AsyncMock(return_value=("gpt ok", 11))
    )

    res = client.post("/api/v1/chat", json=_payload("gpt"), headers={"x-user-id": "u1"})
    app.dependency_overrides.clear()
    assert res.status_code == 200
    data = res.json()
    assert data["reply"] == "gpt ok"
    assert data["tokens_used"] == 11
    assert "x-message-id" in res.headers


def test_chat_claude_route(monkeypatch):
    from app.routers import chat

    app.dependency_overrides[get_current_user] = _auth_override
    monkeypatch.setattr(
        chat, "call_claude", AsyncMock(return_value=("claude ok", 12))
    )

    res = client.post(
        "/api/v1/chat", json=_payload("claude"), headers={"x-user-id": "u1"}
    )
    app.dependency_overrides.clear()
    assert res.status_code == 200
    data = res.json()
    assert data["reply"] == "claude ok"
    assert data["tokens_used"] == 12
    assert "x-message-id" in res.headers


def test_chat_gemini_route(monkeypatch):
    from app.routers import chat

    app.dependency_overrides[get_current_user] = _auth_override
    monkeypatch.setattr(
        chat, "call_gemini", AsyncMock(return_value=("gemini ok", 13))
    )

    res = client.post(
        "/api/v1/chat", json=_payload("gemini"), headers={"x-user-id": "u1"}
    )
    app.dependency_overrides.clear()
    assert res.status_code == 200
    data = res.json()
    assert data["reply"] == "gemini ok"
    assert data["tokens_used"] == 13
    assert "x-message-id" in res.headers


def test_validation_message_too_long():
    app.dependency_overrides[get_current_user] = _auth_override
    too_long = "x" * 2001
    res = client.post(
        "/api/v1/chat", json=_payload("gpt", too_long), headers={"x-user-id": "u1"}
    )
    app.dependency_overrides.clear()
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
    app.dependency_overrides[get_current_user] = _auth_override
    monkeypatch.setattr(
        chat, "call_gpt", AsyncMock(return_value=("gpt ok", 11))
    )

    chat_res = client.post(
        "/api/v1/chat",
        json=_payload("gpt"),
        headers={"x-user-id": "u1", "x-session-id": "s1"},
    )
    app.dependency_overrides.clear()
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


def test_chat_requires_auth():
    res = client.post("/api/v1/chat", json=_payload("gpt"))
    assert res.status_code == 401
