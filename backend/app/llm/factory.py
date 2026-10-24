"""Select the configured text-generation provider.

Only Gemini is implemented. ``LAWYERAI_LLM_PROVIDER`` defaults to ``gemini``
so existing deployments keep working without a new variable.
"""

from __future__ import annotations

import os

from app.llm.errors import LLMError
from app.llm.gemini_provider import GeminiProvider
from app.llm.types import GenerationRequest, LLMProvider

_provider: LLMProvider | None = None
_provider_name: str | None = None


def provider_name() -> str:
    name = os.getenv("LAWYERAI_LLM_PROVIDER", "gemini").strip().lower()
    return name or "gemini"


def use_llm_for_responses() -> bool:
    """When true, an LLM may be used as fallback — never as the primary engine."""
    return os.getenv("LAWYERAI_USE_LLM", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_llm_provider() -> LLMProvider:
    """Return the process-wide provider. Raises ``LLMError`` if the name is unknown."""
    global _provider, _provider_name
    name = provider_name()
    if _provider is not None and _provider_name == name:
        return _provider

    if name == "gemini":
        _provider = GeminiProvider()
        _provider_name = name
        return _provider

    raise LLMError(
        f"Unsupported LLM provider '{name}'. This build supports: gemini."
    )


def reset_llm_provider() -> None:
    """Drop the cached provider (tests and env reloads)."""
    global _provider, _provider_name
    reset = getattr(_provider, "reset", None)
    if callable(reset):
        reset()
    _provider = None
    _provider_name = None


def fallback_enabled() -> bool:
    """True only when the feature flag is on and the selected provider is configured."""
    if not use_llm_for_responses():
        return False
    try:
        provider = get_llm_provider()
    except LLMError:
        return False
    return provider.is_configured()


def complete(request: GenerationRequest) -> str:
    """Generate text with the selected provider."""
    return get_llm_provider().generate(request)
