"""Provider-neutral text-generation types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.llm.errors import LLMError


@dataclass(frozen=True)
class GenerationSettings:
    """Optional generation controls. Unset fields keep the provider default."""

    temperature: float | None = None
    timeout_seconds: float | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class GenerationRequest:
    """Inputs the application actually needs from a text model.

    ``system_instruction`` is optional. When omitted, only ``user_prompt`` is
    sent. Providers decide how to map these fields onto their SDK.
    """

    user_prompt: str
    system_instruction: str | None = None
    settings: GenerationSettings | None = None


class LLMProvider(Protocol):
    """Swappable text generator. Chat and strategy depend on this, not an SDK."""

    name: str

    def is_configured(self) -> bool:
        """True when this provider has the credentials it needs."""

    def generate(self, request: GenerationRequest) -> str:
        """Return model text or raise ``LLMError`` (never a silent fake answer)."""


__all__ = [
    "GenerationRequest",
    "GenerationSettings",
    "LLMError",
    "LLMProvider",
]
