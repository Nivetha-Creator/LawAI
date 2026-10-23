"""
Single entry point for assistant text generation.

Default: local engines (legal + debate services).
Optional: cloud LLM when explicitly enabled and configured (future-friendly).
"""

from __future__ import annotations

from typing import Any

from app.services import ai_service
from app.services.debate_service import generate_debate_feedback, generate_debate_reply
from app.services.legal_service import answer_legal_question


def llm_enabled() -> bool:
    return ai_service.is_configured() and ai_service.use_llm_for_responses()


def generate_chat_reply(message: str, transcript: list[dict[str, Any]]) -> str:
    if llm_enabled():
        history = "\n".join(
            f'{m["role"].upper()}: {m["content"]}'
            for m in transcript[-12:]
        )
        prompt = (
            "You are LawyerAI, an Indian legal information assistant. "
            "Do not invent statutes or citations.\n\n"
            f"Conversation:\n{history}\n\nAnswer the latest user message."
        )
        return ai_service.generate_text(prompt)

    recent_user = [
        m["content"]
        for m in transcript
        if m.get("role") == "user"
    ]
    return answer_legal_question(message, recent_user_messages=recent_user[:-1])


def generate_debate_turn(
    user_side: str,
    topic: str,
    user_message: str,
    transcript: list[dict[str, Any]],
) -> str:
    if llm_enabled():
        opposing = "Defence" if user_side == "Prosecution" else "Prosecution"
        history = "\n".join(
            f'{m["role"].upper()}: {m["content"]}' for m in transcript[-12:]
        )
        prompt = (
            f"Educational debate. User is {user_side}; you argue {opposing}. "
            f"Topic: {topic}. Do not invent citations.\n\n{history}\n\n"
            f"Respond as {opposing}."
        )
        return ai_service.generate_text(prompt)

    return generate_debate_reply(user_side, topic, user_message, transcript)


def generate_debate_review(
    transcript: list[dict[str, Any]],
    user_side: str,
    topic: str,
) -> str:
    if llm_enabled():
        formatted = "\n".join(
            f'{m["role"].upper()}: {m["content"]}' for m in transcript[-30:]
        )
        prompt = (
            "Constructive debate coach. Score 1-10 on reasoning, evidence, clarity. "
            "Educational only.\n\n" + formatted
        )
        return ai_service.generate_text(prompt)

    return generate_debate_feedback(transcript, user_side, topic)
