"""LLM adapter tests. No network and no real API key."""

import builtins
import types

import pytest

from app.llm.errors import LLMError
from app.llm.factory import fallback_enabled, get_llm_provider, reset_llm_provider
from app.llm.gemini_provider import GeminiError, GeminiProvider, render_contents
from app.llm.types import GenerationRequest, GenerationSettings
from app.services import ai_service, response_provider
from app.services.strategy_service import (
    build_strategy_enrichment_prompt,
    strategy_generation_request,
)


@pytest.fixture(autouse=True)
def _reset_provider(monkeypatch):
    monkeypatch.delenv("LAWYERAI_USE_LLM", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LAWYERAI_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_TIMEOUT_SECONDS", raising=False)
    reset_llm_provider()
    ai_service.reload_settings_from_env()
    yield
    reset_llm_provider()
    ai_service.reload_settings_from_env()


def _install_fake_genai(monkeypatch, generate_content):
    captured: dict = {}

    class FakeModels:
        def generate_content(self, model, contents, config=None):
            captured["model"] = model
            captured["contents"] = contents
            captured["config"] = config
            return generate_content(model, contents, config)

    class FakeClient:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.models = FakeModels()

    google_mod = types.ModuleType("google")
    genai_mod = types.ModuleType("google.genai")
    genai_mod.Client = FakeClient
    google_mod.genai = genai_mod
    monkeypatch.setitem(__import__("sys").modules, "google", google_mod)
    monkeypatch.setitem(__import__("sys").modules, "google.genai", genai_mod)
    return captured


def test_chat_prompt_matches_previous_gemini_contents():
    request = ai_service.chat_generation_request("What is bail?", "USER: earlier")
    assert render_contents(request) == ai_service.build_legal_fallback_prompt(
        "What is bail?",
        "USER: earlier",
    )
    assert request.system_instruction.startswith("You are LawyerAI")
    assert "What is bail?" in request.user_prompt


def test_strategy_prompt_matches_previous_gemini_contents():
    request = strategy_generation_request("facts", "local analysis")
    assert render_contents(request) == build_strategy_enrichment_prompt(
        "facts",
        "local analysis",
    )


def test_provider_defaults_to_gemini_and_rejects_unknown(monkeypatch):
    provider = get_llm_provider()
    assert provider.name == "gemini"
    assert provider.is_configured() is False

    monkeypatch.setenv("LAWYERAI_LLM_PROVIDER", "other-vendor")
    reset_llm_provider()
    with pytest.raises(LLMError, match="Unsupported LLM provider"):
        get_llm_provider()
    assert fallback_enabled() is False


def test_placeholder_key_is_not_configured(monkeypatch):
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "your_actual_gemini_api_key")
    ai_service.reload_settings_from_env()
    assert ai_service.is_configured() is False
    assert fallback_enabled() is False
    with pytest.raises(GeminiError, match="not configured"):
        ai_service.generate_text("hello")


def test_flag_without_key_does_not_enable_fallback(monkeypatch):
    monkeypatch.setenv("LAWYERAI_USE_LLM", "yes")
    ai_service.reload_settings_from_env()
    assert fallback_enabled() is False


def test_key_without_flag_does_not_enable_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ai_service.reload_settings_from_env()
    assert ai_service.is_configured() is True
    assert fallback_enabled() is False


def test_gemini_adapter_sends_model_timeout_and_contents(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "25")

    def ok(model, contents, config):
        return types.SimpleNamespace(text="  useful answer  ")

    captured = _install_fake_genai(monkeypatch, ok)
    provider = GeminiProvider()
    text = provider.generate(
        GenerationRequest(
            system_instruction="SYSTEM RULES",
            user_prompt="User question here",
            settings=GenerationSettings(temperature=0.2, max_output_tokens=128),
        )
    )
    assert text == "useful answer"
    assert captured["api_key"] == "test-key"
    assert captured["model"] == "gemini-2.5-flash"
    assert captured["contents"] == "SYSTEM RULES\n\nUser question here"
    assert captured["config"]["http_options"]["timeout"] == 25000
    assert captured["config"]["temperature"] == 0.2
    assert captured["config"]["max_output_tokens"] == 128


def test_gemini_adapter_retries_without_config_on_typeerror(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"n": 0}

    def flaky(model, contents, config):
        calls["n"] += 1
        if config is not None:
            raise TypeError("config not supported")
        return types.SimpleNamespace(text="retried")

    _install_fake_genai(monkeypatch, flaky)
    text = GeminiProvider().generate(GenerationRequest(user_prompt="only user"))
    assert text == "retried"
    assert calls["n"] == 2


def test_gemini_adapter_maps_timeout_quota_auth_and_empty(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def timeout(model, contents, config):
        raise TimeoutError()

    _install_fake_genai(monkeypatch, timeout)
    with pytest.raises(GeminiError, match="timed out"):
        GeminiProvider().generate(GenerationRequest(user_prompt="q"))

    def quota(model, contents, config):
        raise RuntimeError("429 quota")

    _install_fake_genai(monkeypatch, quota)
    with pytest.raises(GeminiError, match="rate limit"):
        GeminiProvider().generate(GenerationRequest(user_prompt="q"))

    secret = "super-secret-key-value"

    def auth(model, contents, config):
        raise RuntimeError(f"403 permission denied for {secret}")

    _install_fake_genai(monkeypatch, auth)
    with pytest.raises(GeminiError, match="API key or permissions") as exc_info:
        GeminiProvider().generate(GenerationRequest(user_prompt="q"))
    assert secret not in str(exc_info.value)

    def empty(model, contents, config):
        return types.SimpleNamespace(text="   ")

    _install_fake_genai(monkeypatch, empty)
    with pytest.raises(GeminiError, match="empty response"):
        GeminiProvider().generate(GenerationRequest(user_prompt="q"))


def test_missing_sdk_raises_install_hint(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    real_import = builtins.__import__

    def blocked(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "google" or name.startswith("google."):
            raise ImportError("blocked for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(GeminiError, match="google-genai is not installed"):
        GeminiProvider().generate(GenerationRequest(user_prompt="q"))


def test_debate_never_calls_llm_provider(monkeypatch):
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ai_service.reload_settings_from_env()

    def boom(_request):
        raise AssertionError("Debate Practice must not call the LLM provider")

    monkeypatch.setattr(response_provider, "complete_llm", boom)
    reply = response_provider.generate_debate_turn(
        "Defence",
        "bail",
        "The accused was elsewhere because the timeline does not match.",
        [],
    )
    assert "opposing counsel" in reply.lower()
    review = response_provider.generate_debate_review(
        [
            {
                "role": "user",
                "content": "The accused was elsewhere because the timeline does not match.",
            }
        ],
        "Defence",
        "bail",
    )
    assert "checklist" in review.lower() or "educational" in review.lower()
