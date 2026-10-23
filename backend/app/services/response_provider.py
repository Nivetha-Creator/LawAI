"""
Single entry point for assistant text generation.

Chat: local knowledge base first; optional Gemini only when the local engine
returns unknown AND LAWYERAI_USE_LLM + GEMINI_API_KEY are set.

Debate: always local (rule-based) in Phase 1.
"""

from __future__ import annotations

from typing import Any

from app.services import ai_service
from app.services.debate_service import generate_debate_feedback, generate_debate_reply
from app.services.legal_service import resolve_legal_question


def llm_enabled() -> bool:
    """True when Gemini fallback is allowed (key + flag)."""
    return ai_service.fallback_enabled()


def generate_chat_reply(
    message: str,
    transcript: list[dict[str, Any]],
) -> tuple[str, str]:
    """
    Returns (reply_text, engine) where engine is ``local`` or ``gemini``.
    """
    recent_user = [m["content"] for m in transcript if m.get("role") == "user"]
    local = resolve_legal_question(message, recent_user_messages=recent_user[:-1])

    if local.status in {"matched", "clarify"}:
        return local.text, "local"

    # Local unknown → optional Gemini fallback.
    if not ai_service.fallback_enabled():
        return local.text, "local"

    history = "\n".join(
        f'{m["role"].upper()}: {m["content"]}' for m in transcript[-12:]
    )
    prompt = ai_service.build_legal_fallback_prompt(message, history)

    try:
        raw = ai_service.generate_text(prompt)
        return ai_service.format_gemini_reply(raw), "gemini"
    except ai_service.GeminiError as exc:
        fallback = (
            f"{local.text}\n\n"
            "**Optional AI fallback unavailable**\n"
            f"{exc}\n\n"
            "LawyerAI is still running on the local knowledge base. "
            "Rephrase with keywords such as road accident, hit and run, "
            "insurance claim, FIR, or bail—or consult a qualified advocate."
        )
        return fallback, "local"
    except Exception:  # noqa: BLE001
        fallback = (
            f"{local.text}\n\n"
            "**Optional AI fallback unavailable**\n"
            "The AI service failed unexpectedly. "
            "Use the local suggestions above or consult a qualified advocate."
        )
        return fallback, "local"


def generate_debate_turn(
    user_side: str,
    topic: str,
    user_message: str,
    transcript: list[dict[str, Any]],
) -> str:
    return generate_debate_reply(user_side, topic, user_message, transcript)


def generate_debate_review(
    transcript: list[dict[str, Any]],
    user_side: str,
    topic: str,
) -> str:
    return generate_debate_feedback(transcript, user_side, topic)
