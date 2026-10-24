"""
Single entry point for assistant text generation.

Chat: local knowledge base first; optional LLM only when the local engine
returns unknown AND LAWYERAI_USE_LLM plus a configured provider are set.

Debate: always local (rule-based). It does not call the LLM provider.

Strategy: clarification and illegal-request refusal stay local. Optional LLM
enrichment runs only when the local analysis asks for it and fallback is enabled.

The API ``engine`` field remains ``local`` or ``gemini`` for compatibility with
the current Gemini-only adapter.
"""

from __future__ import annotations

from typing import Any

from app.llm.errors import LLMError
from app.llm.factory import complete as complete_llm
from app.llm.factory import fallback_enabled
from app.rag.citations import citations_are_supported
from app.rag.filters import filters_from_text
from app.rag.present import evidence_block, format_excerpts, format_source_footer
from app.rag.retrieve import rag_enabled, retrieve_for_query
from app.services import ai_service
from app.services.debate_service import generate_debate_feedback, generate_debate_reply
from app.services.legal_service import resolve_legal_question
from app.services.strategy_service import (
    analyze_legal_strategy,
    format_strategy_enrichment,
    strategy_generation_request,
)


def llm_enabled() -> bool:
    """True when the configured LLM may be used as fallback."""
    return fallback_enabled()


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

    evidence = _retrieve(message) if rag_enabled() else None
    history = "\n".join(
        f'{m["role"].upper()}: {m["content"]}' for m in transcript[-12:]
    )
    hits = evidence.chunks if evidence and evidence.status == "hits" else []

    if hits and fallback_enabled():
        request = ai_service.chat_evidence_generation_request(
            message,
            history,
            evidence_block(hits),
        )
        try:
            raw = complete_llm(request)
        except LLMError as exc:
            return _chat_local_with_optional_excerpts(local.text, hits, str(exc)), "local"
        except Exception:  # noqa: BLE001
            return _chat_local_with_optional_excerpts(local.text, hits, ""), "local"
        if citations_are_supported(raw, hits):
            return (
                ai_service.format_gemini_reply(raw) + format_source_footer(hits),
                "gemini",
            )
        return local.text + format_excerpts(hits), "local"

    if hits:
        return local.text + format_excerpts(hits), "local"

    # Local unknown → optional LLM fallback (Gemini adapter today).
    if not fallback_enabled():
        return _with_retrieval_note(local.text, evidence), "local"

    request = ai_service.chat_generation_request(message, history)

    try:
        raw = complete_llm(request)
        return _with_retrieval_note(ai_service.format_gemini_reply(raw), evidence), "gemini"
    except LLMError as exc:
        fallback = (
            f"{local.text}\n\n"
            "**Optional AI fallback unavailable**\n"
            f"{exc}\n\n"
            "LawyerAI is still running on the local knowledge base. "
            "Rephrase with keywords such as road accident, hit and run, "
            "insurance claim, FIR, or bail—or consult a qualified advocate."
        )
        return _with_retrieval_note(fallback, evidence), "local"
    except Exception:  # noqa: BLE001
        fallback = (
            f"{local.text}\n\n"
            "**Optional AI fallback unavailable**\n"
            "The AI service failed unexpectedly. "
            "Use the local suggestions above or consult a qualified advocate."
        )
        return _with_retrieval_note(fallback, evidence), "local"


def _retrieve(message: str):
    """Run retrieval with only the filters the message can support."""
    jurisdiction, as_of = filters_from_text(message)
    return retrieve_for_query(message, jurisdiction=jurisdiction, as_of=as_of)


def _with_retrieval_note(text: str, evidence) -> str:
    if evidence is not None and evidence.status == "error":
        return (
            f"{text}\n\n"
            "Document retrieval is unavailable. "
            "This reply does not use indexed documents."
        )
    return text


def _chat_local_with_optional_excerpts(local_text: str, hits, error: str) -> str:
    parts = [local_text]
    if error:
        parts.append(f"\n\n**Optional AI fallback unavailable**\n{error}")
    else:
        parts.append(
            "\n\n**Optional AI fallback unavailable**\n"
            "The AI service failed unexpectedly."
        )
    if hits:
        parts.append(format_excerpts(hits))
    return "".join(parts)


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


def generate_strategy_reply(
    message: str,
    transcript: list[dict[str, Any]],
) -> tuple[str, str]:
    """
    Legal Strategy Analysis. Local-first structured report.
    Optional Gemini only enriches when local law section has no curated match
    and fallback is enabled — never used to invent facts when clarifying.
    """
    recent_user = [m["content"] for m in transcript if m.get("role") == "user"]
    result = analyze_legal_strategy(message, recent_user_messages=recent_user[:-1])

    if result.status in {"clarify", "refused_illegal"}:
        return result.text, "local"

    text = result.text
    engine = "local"
    evidence = None
    if result.needs_unverified_enrichment and rag_enabled():
        evidence = _retrieve(message)
    hits = evidence.chunks if evidence and evidence.status == "hits" else []

    if result.needs_unverified_enrichment and fallback_enabled():
        if hits:
            request = strategy_generation_request(
                message,
                result.text,
                evidence_block(hits),
            )
        else:
            request = strategy_generation_request(message, result.text)
        try:
            raw = complete_llm(request)
            if hits and not citations_are_supported(raw, hits):
                text = result.text + format_excerpts(hits)
                engine = "local"
            else:
                text = result.text + format_strategy_enrichment(raw)
                if hits:
                    text += format_source_footer(hits)
                engine = "gemini"
        except LLMError as exc:
            text = (
                f"{result.text}\n\n"
                "**Optional AI enrichment unavailable**\n"
                f"{exc}\n"
                "The local strategy analysis above remains available."
            )
            if hits:
                text += format_excerpts(hits)
            engine = "local"
        except Exception:  # noqa: BLE001
            text = (
                f"{result.text}\n\n"
                "**Optional AI enrichment unavailable**\n"
                "The AI service failed unexpectedly. Use the local analysis above."
            )
            if hits:
                text += format_excerpts(hits)
            engine = "local"
    elif hits:
        text = result.text + format_excerpts(hits)

    if evidence is not None and evidence.status == "error":
        text += (
            "\n\nDocument retrieval is unavailable. "
            "This analysis does not use indexed documents."
        )

    return text, engine

