import os

import pytest

from app.services import ai_service, response_provider
from app.services.ai_service import GeminiError


@pytest.fixture(autouse=True)
def _clear_gemini_env(monkeypatch):
    monkeypatch.delenv("LAWYERAI_USE_LLM", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    ai_service.reload_settings_from_env()
    yield
    monkeypatch.delenv("LAWYERAI_USE_LLM", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    ai_service.reload_settings_from_env()


def test_gemini_disabled_without_key_uses_local_unknown():
    reply, engine = response_provider.generate_chat_reply(
        "Obscure 1953 municipal pigeon coop bye-law number?",
        [{"role": "user", "content": "Obscure 1953 municipal pigeon coop bye-law number?"}],
    )
    assert engine == "local"
    assert "do not have curated information" in reply.lower()
    assert "optional ai fallback" not in reply.lower() or "unavailable" in reply.lower()


def test_local_match_never_calls_gemini(monkeypatch):
    called = {"n": 0}

    def boom(_prompt):
        called["n"] += 1
        raise AssertionError("Gemini should not be called for local matches")

    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")
    ai_service.reload_settings_from_env()
    monkeypatch.setattr(ai_service, "generate_text", boom)

    reply, engine = response_provider.generate_chat_reply(
        "Explain the difference between BNS and IPC",
        [{"role": "user", "content": "Explain the difference between BNS and IPC"}],
    )
    assert engine == "local"
    assert "curated knowledge base" in reply
    assert called["n"] == 0


def test_gemini_fallback_uses_mocked_response(monkeypatch):
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ai_service.reload_settings_from_env()

    monkeypatch.setattr(
        ai_service,
        "generate_text",
        lambda prompt: "General steps may include documenting facts and consulting an advocate.",
    )

    reply, engine = response_provider.generate_chat_reply(
        "Obscure 1953 municipal pigeon coop bye-law number?",
        [
            {
                "role": "user",
                "content": "Obscure 1953 municipal pigeon coop bye-law number?",
            }
        ],
    )
    assert engine == "gemini"
    assert "optional ai fallback" in reply.lower()
    assert "verified curated" in reply.lower()
    assert "not** legal advice" in reply.lower() or "not legal advice" in reply.lower().replace("*", "")


def test_gemini_failure_returns_graceful_fallback(monkeypatch):
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ai_service.reload_settings_from_env()

    def fail(_prompt):
        raise GeminiError("Gemini rate limit or quota exceeded.")

    monkeypatch.setattr(ai_service, "generate_text", fail)

    reply, engine = response_provider.generate_chat_reply(
        "Obscure 1953 municipal pigeon coop bye-law number?",
        [
            {
                "role": "user",
                "content": "Obscure 1953 municipal pigeon coop bye-law number?",
            }
        ],
    )
    assert engine == "local"
    assert "do not have curated information" in reply.lower()
    assert "optional ai fallback unavailable" in reply.lower()
    assert "rate limit" in reply.lower()


def test_generate_text_requires_configuration():
    with pytest.raises(GeminiError):
        ai_service.generate_text("hello")
