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
    assert response.json()["response_engine"] == "local"


def test_chat_and_conversation_flow(client):
    chat = client.post("/chat", json={"message": "What is BNS compared to IPC?"})
    assert chat.status_code == 200
    body = chat.json()
    assert body["conversation_id"]
    assert "curated knowledge base" in body["reply"]
    assert body["engine"] == "local"

    conv_id = body["conversation_id"]
    detail = client.get(f"/conversations/{conv_id}")
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) >= 2

    listed = client.get("/conversations")
    assert listed.status_code == 200
    assert any(c["id"] == conv_id for c in listed.json())

    renamed = client.patch(
        f"/conversations/{conv_id}",
        json={"title": "BNS question"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "BNS question"

    deleted = client.delete(f"/conversations/{conv_id}")
    assert deleted.status_code == 200


def test_debate_turn_and_end(client):
    start = client.post(
        "/debate",
        json={
            "message": "CCTV alone should not secure a conviction because intent is missing.",
            "side": "defence",
            "topic": "CCTV as sole evidence",
        },
    )
    assert start.status_code == 200
    data = start.json()
    conv_id = data["conversation_id"]
    assert data["ended"] is False
    assert "Opposing counsel" in data["reply"]

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

    loaded = client.get(f"/conversations/{conv_id}")
    assert loaded.json()["ended"] == 1
