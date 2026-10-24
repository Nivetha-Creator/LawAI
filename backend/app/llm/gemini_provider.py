"""Google Gemini adapter.

SDK imports stay inside this module. Callers depend on ``LLMProvider``.
The contents string is system instruction, a blank line, then the user prompt
— the same shape LawyerAI previously sent as one concatenated prompt.
"""

from __future__ import annotations

import os
from typing import Any

from app.llm.errors import LLMError
from app.llm.types import GenerationRequest, GenerationSettings

_PLACEHOLDER_KEYS = frozenset(
    {
        "your_actual_gemini_api_key",
        "changeme",
        "xxx",
    }
)


class GeminiError(LLMError):
    """Raised when Gemini cannot produce a usable response."""


def _api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def _model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"


def _timeout_seconds(override: float | None) -> float:
    if override is not None:
        return float(override)
    raw = os.getenv("GEMINI_TIMEOUT_SECONDS", "25").strip() or "25"
    try:
        return float(raw)
    except ValueError as exc:
        raise GeminiError("GEMINI_TIMEOUT_SECONDS must be a number.") from exc


def key_is_usable(api_key: str | None = None) -> bool:
    key = _api_key() if api_key is None else api_key.strip()
    return bool(key) and key not in _PLACEHOLDER_KEYS


def render_contents(request: GenerationRequest) -> str:
    """Map a neutral request onto Gemini's single ``contents`` string."""
    system = (request.system_instruction or "").strip()
    user = request.user_prompt or ""
    if system:
        return f"{system}\n\n{user}"
    return user


class GeminiProvider:
    """Gemini implementation of ``LLMProvider``."""

    name = "gemini"

    def __init__(self) -> None:
        self._client: Any = None
        self._client_key: str | None = None

    def reset(self) -> None:
        self._client = None
        self._client_key = None

    def is_configured(self) -> bool:
        return key_is_usable()

    def _client_for(self, api_key: str) -> Any:
        try:
            from google import genai
        except ImportError as exc:
            raise GeminiError(
                "google-genai is not installed. Run: pip install google-genai"
            ) from exc

        if self._client is None or self._client_key != api_key:
            self._client = genai.Client(api_key=api_key)
            self._client_key = api_key
        return self._client

    def generate(self, request: GenerationRequest) -> str:
        if not self.is_configured():
            raise GeminiError("Gemini is not configured (missing GEMINI_API_KEY).")

        settings: GenerationSettings = request.settings or GenerationSettings()
        timeout_seconds = _timeout_seconds(settings.timeout_seconds)
        contents = render_contents(request)
        model = _model()
        api_key = _api_key()

        config: dict[str, Any] = {
            "http_options": {"timeout": int(timeout_seconds * 1000)},
        }
        if settings.temperature is not None:
            config["temperature"] = settings.temperature
        if settings.max_output_tokens is not None:
            config["max_output_tokens"] = settings.max_output_tokens

        try:
            client = self._client_for(api_key)
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
            except TypeError:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                )
        except GeminiError:
            raise
        except Exception as exc:  # noqa: BLE001 — map SDK/network failures
            raise _map_sdk_error(exc) from exc

        text = getattr(response, "text", None)
        if text is None and hasattr(response, "candidates"):
            try:
                text = response.text
            except Exception:  # noqa: BLE001
                text = None

        if not text or not str(text).strip():
            raise GeminiError("Gemini returned an empty response.")

        return str(text).strip()


def _map_sdk_error(exc: Exception) -> GeminiError:
    name = type(exc).__name__
    message = str(exc).lower()
    if "resource_exhausted" in message or "429" in message or "quota" in message:
        return GeminiError("Gemini rate limit or quota exceeded.")
    if isinstance(exc, TimeoutError) or "timeout" in message or "timed out" in message:
        return GeminiError("Gemini request timed out.")
    if "401" in message or "403" in message or "permission" in message:
        return GeminiError("Gemini rejected the API key or permissions.")
    return GeminiError(f"Gemini API error ({name}).")
