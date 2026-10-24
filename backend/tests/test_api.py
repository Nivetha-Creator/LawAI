import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(temp_db):
    os.environ.pop("LAWYERAI_USE_LLM", None)
    os.environ.pop("GEMINI_API_KEY", None)
    from app.main import app

    return TestClient(app)


def test_health_local_engine(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["response_engine"] == "local"
    assert body.get("gemini_fallback") is False
    assert body.get("rag_enabled") is False


def test_docs_available(client):
    response = client.get("/docs")
    assert response.status_code == 200


def test_home_reports_local_features(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["response_engine"] == "local"
    assert any("Local" in feature for feature in body["features"])


def test_supported_legal_chat(client):
    chat = client.post(
        "/chat",
        json={"message": "What is BNS compared to IPC?"},
    )
    assert chat.status_code == 200
    body = chat.json()
    assert body["conversation_id"]
    assert "curated knowledge base" in body["reply"]
    assert body["engine"] == "local"
    assert "will not guess" not in body["reply"].lower()


def test_road_accident_chat_local(client):
    chat = client.post(
        "/chat",
        json={"message": "What should I do after a road accident with vehicle damage?"},
    )
    assert chat.status_code == 200
    body = chat.json()
    assert body["engine"] == "local"
    assert "curated knowledge base" in body["reply"]
    assert "accident" in body["reply"].lower()


def test_unsupported_legal_chat(client):
    chat = client.post(
        "/chat",
        json={
            "message": (
                "What is the exact obscure municipal bye-law number for "
                "rooftop pigeon coops in a fictional district in 1953?"
            )
        },
    )
    assert chat.status_code == 200
    reply = chat.json()["reply"].lower()
    assert "do not have curated information" in reply
    assert "will not guess" in reply


def test_chat_validation_empty_message(client):
    # Empty string fails Pydantic min_length; whitespace fails route strip check.
    empty = client.post("/chat", json={"message": ""})
    assert empty.status_code == 422

    whitespace = client.post("/chat", json={"message": "   "})
    assert whitespace.status_code == 400
    assert "legal question" in whitespace.json()["detail"].lower()


def test_chat_missing_conversation(client):
    response = client.post(
        "/chat",
        json={"message": "Explain bail basics in India", "conversation_id": 999999},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_chat_and_conversation_crud(client):
    chat = client.post("/chat", json={"message": "What is an FIR in India?"})
    assert chat.status_code == 200
    body = chat.json()
    conv_id = body["conversation_id"]

    detail = client.get(f"/conversations/{conv_id}")
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert len(messages) >= 2
    assert messages[0]["role"] == "user"
    assert "FIR" in messages[0]["content"] or "fir" in messages[0]["content"].lower()

    listed = client.get("/conversations")
    assert listed.status_code == 200
    assert any(c["id"] == conv_id for c in listed.json())

    created = client.post("/conversations")
    assert created.status_code == 200
    assert created.json()["id"]

    renamed = client.patch(
        f"/conversations/{conv_id}",
        json={"title": "FIR overview"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "FIR overview"

    missing = client.get("/conversations/999999")
    assert missing.status_code == 404

    bad_rename = client.patch(
        "/conversations/999999",
        json={"title": "Nope"},
    )
    assert bad_rename.status_code == 404

    deleted = client.delete(f"/conversations/{conv_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    gone = client.get(f"/conversations/{conv_id}")
    assert gone.status_code == 404

    delete_missing = client.delete("/conversations/999999")
    assert delete_missing.status_code == 404


def test_debate_uses_actual_opening_argument(client):
    opening = (
        "CCTV alone should not secure a conviction because intent is missing "
        "and the footage quality is poor."
    )
    start = client.post(
        "/debate",
        json={
            "message": opening,
            "side": "defence",
            "topic": "CCTV as sole evidence",
        },
    )
    assert start.status_code == 200
    data = start.json()
    conv_id = data["conversation_id"]
    assert data["ended"] is False
    assert "Opposing counsel" in data["reply"]
    assert "intent is missing" in data["reply"] or "footage" in data["reply"].lower()

    detail = client.get(f"/conversations/{conv_id}")
    user_messages = [
        m["content"] for m in detail.json()["messages"] if m["role"] == "user"
    ]
    assert opening in user_messages
    assert detail.json()["topic"] == "CCTV as sole evidence"
    assert detail.json()["ended"] == 0


def test_debate_followup_and_end_preserves_state(client):
    start = client.post(
        "/debate",
        json={
            "message": "The prosecution must prove guilt beyond reasonable doubt.",
            "side": "defence",
            "topic": "CCTV as sole evidence",
        },
    )
    conv_id = start.json()["conversation_id"]

    follow = client.post(
        "/debate",
        json={
            "message": "However, the chain of custody for the video was documented.",
            "side": "defence",
            "topic": "CCTV as sole evidence",
            "conversation_id": conv_id,
        },
    )
    assert follow.status_code == 200

    end = client.post(
        "/debate",
        json={
            "message": "",
            "side": "defence",
            "topic": "CCTV as sole evidence",
            "conversation_id": conv_id,
            "end_debate": True,
        },
    )
    assert end.status_code == 200
    assert end.json()["ended"] is True
    assert "DEBATE REVIEW" in end.json()["reply"]
    assert "rule-based" in end.json()["reply"].lower()

    loaded = client.get(f"/conversations/{conv_id}")
    assert loaded.json()["ended"] == 1


def test_debate_invalid_side(client):
    response = client.post(
        "/debate",
        json={"message": "Hello", "side": "judge", "topic": "Bail"},
    )
    assert response.status_code == 400
    assert "Prosecution or Defence" in response.json()["detail"]


def test_debate_requires_argument_when_not_ending(client):
    response = client.post(
        "/debate",
        json={"message": "", "side": "prosecution", "topic": ""},
    )
    assert response.status_code == 400


def test_cors_allows_local_vite_origins(client):
    for origin in (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ):
        response = client.options(
            "/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204)
        assert response.headers.get("access-control-allow-origin") == origin


def test_strategy_endpoint_clarify_and_complete(client):
    thin = client.post(
        "/strategy",
        json={"message": "I have a legal problem. Advise me."},
    )
    assert thin.status_code == 200
    assert thin.json()["engine"] == "local"
    assert thin.json()["mode"] == "strategy"
    assert "more detail needed" in thin.json()["reply"].lower()

    rich = (
        "In Chennai, Tamil Nadu, India, on 12 March 2025 I had a road accident. "
        "FIR registered; investigation pending. I have photos, medical bills, and "
        "a witness. Other driver says I was speeding. Analyse strategy."
    )
    full = client.post("/strategy", json={"message": rich})
    assert full.status_code == 200
    body = full.json()
    assert body["engine"] == "local"
    assert "### 1. Case summary" in body["reply"]
    assert body["conversation_id"]

    detail = client.get(f"/conversations/{body['conversation_id']}")
    assert detail.json()["mode"] == "strategy"
    assert len(detail.json()["messages"]) >= 2


def test_strategy_does_not_break_chat_or_debate(client):
    chat = client.post("/chat", json={"message": "What is BNS compared to IPC?"})
    assert chat.status_code == 200
    assert chat.json()["engine"] == "local"
    assert "curated knowledge base" in chat.json()["reply"]

    debate = client.post(
        "/debate",
        json={
            "message": "CCTV alone cannot prove intent beyond doubt.",
            "side": "defence",
            "topic": "CCTV evidence",
        },
    )
    assert debate.status_code == 200
    assert "Opposing counsel" in debate.json()["reply"]
