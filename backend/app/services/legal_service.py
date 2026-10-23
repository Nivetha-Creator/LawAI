"""
Rule-based Indian legal information engine (no external API).

Matching is intentionally conservative: weak single-keyword hits should not
produce a confident answer. Insufficient matches yield a clarifying question
or an explicit unknown notice for optional Gemini fallback.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Literal

from app.knowledge.topics import LEGAL_TOPICS, LegalTopic

STOP_WORDS = frozenset(
    """
    a an the is are was were be been being have has had do does did will would
    could should may might must shall can need dare ought used to of in for on
    with at by from up about into over after and or but if then than so because
    as until while although though both either neither not no nor only own same
    such too very just also what which who whom whose this that these those am
    i me my we our you your he she it they them their how when where why all any
    some one two tell explain difference between under indian india law legal
    please help want know regarding related about enna ipdi
    """.split()
)

# Phrase / spelling normalisations (English + common Tanglish).
PHRASE_ALIASES: tuple[tuple[str, str], ...] = (
    (r"\bhit\s*&\s*run\b", "hit and run"),
    (r"\bhit\s*n\s*run\b", "hit and run"),
    (r"\bodittu\s*poyiduch[uai]?\b", "hit and run fled"),
    (r"\bodittu\s*poitaanga\b", "hit and run fled"),
    (r"\baagiduch[uai]?\b", "happened"),
    (r"\baayiduch[uai]?\b", "happened"),
    (r"\bmet\s+accident\b", "road accident"),
    (r"\baccident\s+aagiduch", "road accident happened"),
    (r"\baccident\s+aayiduch", "road accident happened"),
    (r"\bcar\s+crash\b", "car accident"),
    (r"\bbike\s+crash\b", "bike accident"),
    (r"\btwo[\s-]?wheeler\b", "two wheeler"),
    (r"\bkaayam\b", "injury"),
    (r"\binsurance\s+claim\b", "insurance claim"),
    (r"\bthird[\s-]?party\b", "third party"),
)

# Very broad tokens that must not alone decide a topic.
WEAK_SOLO_KEYWORDS = frozenset(
    {
        "police",
        "complaint",
        "accident",
        "injury",
        "insurance",
        "claim",
        "vehicle",
        "car",
        "bike",
        "damage",
        "lawyer",
        "advocate",
        "arrest",
        "custody",
    }
)

MATCH_MIN_SCORE = 3.5
CLARIFY_MIN_SCORE = 2.0
OFFICIAL_SOURCE = "https://www.indiacode.nic.in/"

AnswerStatus = Literal["matched", "clarify", "unknown"]


@dataclass(frozen=True)
class LegalAnswer:
    status: AnswerStatus
    text: str
    topic_id: str | None = None
    score: float = 0.0


def normalize_query(text: str) -> str:
    """Lowercase, strip, collapse whitespace/punctuation, apply aliases."""
    value = unicodedata.normalize("NFKC", text or "")
    value = value.lower().strip()
    value = value.replace("’", "'").replace("“", '"').replace("”", '"')
    for pattern, replacement in PHRASE_ALIASES:
        value = re.sub(pattern, replacement, value)
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", normalize_query(text))
    return {t for t in tokens if len(t) > 1 and t not in STOP_WORDS}


def score_topic(normalized_query: str, query_tokens: set[str], topic: LegalTopic) -> tuple[float, int]:
    """
    Return (score, distinct_keyword_hits).
    Multi-word phrases score higher; weak solo keywords alone score little.
    """
    score = 0.0
    hits = 0
    hit_keywords: list[str] = []

    for keyword in topic["keywords"]:
        kw = normalize_query(keyword)
        parts = kw.split()
        if not parts:
            continue

        if len(parts) >= 2:
            if kw in normalized_query:
                score += 4.0
                hits += 1
                hit_keywords.append(kw)
            elif all(p in query_tokens for p in parts):
                score += 3.0
                hits += 1
                hit_keywords.append(kw)
        else:
            token = parts[0]
            if token in query_tokens:
                if token in WEAK_SOLO_KEYWORDS:
                    score += 1.0
                else:
                    score += 2.2
                hits += 1
                hit_keywords.append(token)

    # Soft title overlap (capped).
    title_tokens = _tokenize(topic["title"])
    overlap = query_tokens & title_tokens
    score += min(len(overlap), 3) * 0.5

    # Penalise answers driven only by a single weak token.
    if hits == 1 and hit_keywords and hit_keywords[0] in WEAK_SOLO_KEYWORDS:
        score = min(score, CLARIFY_MIN_SCORE - 0.1)

    return score, hits


def match_topics(query: str, limit: int = 3) -> list[tuple[LegalTopic, float]]:
    normalized = normalize_query(query)
    query_tokens = _tokenize(normalized)
    if not query_tokens:
        return []

    ranked: list[tuple[LegalTopic, float]] = []
    for topic in LEGAL_TOPICS:
        score, _hits = score_topic(normalized, query_tokens, topic)
        if score > 0:
            ranked.append((topic, score))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:limit]


def _format_topic_answer(topic: LegalTopic) -> str:
    return (
        f"**{topic['title']}** (from LawyerAI's curated knowledge base)\n\n"
        f"{topic['summary']}\n\n"
        f"**More context**\n{topic['details']}\n\n"
        f"**Practical next steps**\n{topic['practical_steps']}\n\n"
        f"This is general information, not legal advice. Verify statutes on "
        f"{OFFICIAL_SOURCE} and consult a qualified Indian advocate."
    )


def _clarifying_response(topic: LegalTopic, query: str) -> str:
    return (
        f"I may have a related topic (**{topic['title']}**), but I do not have "
        f"enough detail yet for a reliable answer.\n\n"
        f"{topic['clarifying_question']}\n\n"
        f"**Your question (summary):** {query[:400]}\n\n"
        f"I will not invent statute sections or case outcomes. You can also check "
        f"{OFFICIAL_SOURCE} or consult a qualified advocate."
    )


def _unknown_response(query: str, near_misses: Iterable[tuple[LegalTopic, float]]) -> str:
    lines = [
        "I do not have curated information in my local knowledge base that "
        "reliably answers your question.",
        "",
        "I will not guess statutes, section numbers, case names, or outcomes.",
        "",
        f"**Your question (summary):** {query[:500]}",
        "",
        "**What you can do next**",
        f"- Check official legislation on {OFFICIAL_SOURCE}",
        "- Speak with a qualified advocate who can review your documents",
        "- Try rephrasing with specific keywords (for example: road accident, "
        "hit and run, motor insurance claim, FIR, bail, BNS)",
    ]
    suggestions = [t for t, s in near_misses if s >= 1.0][:2]
    if suggestions:
        lines.extend(
            [
                "",
                "**Related topics in this app's knowledge base (not a direct answer):**",
            ]
        )
        for topic in suggestions:
            lines.append(f"- {topic['title']}")
    return "\n".join(lines)


def resolve_legal_question(
    message: str,
    recent_user_messages: list[str] | None = None,
) -> LegalAnswer:
    """Classify and answer from the knowledge base only (no network)."""
    original = (message or "").strip()
    combined = original
    if recent_user_messages:
        prior = " ".join(recent_user_messages[-2:])
        combined = f"{prior} {combined}"

    matches = match_topics(combined, limit=3)
    if not matches:
        return LegalAnswer("unknown", _unknown_response(original, []), score=0.0)

    primary, score = matches[0]
    second_score = matches[1][1] if len(matches) > 1 else 0.0

    # Ambiguous: two strong topics too close together → clarify.
    if (
        score >= CLARIFY_MIN_SCORE
        and second_score >= CLARIFY_MIN_SCORE
        and (score - second_score) < 0.75
        and matches[0][0]["id"] != matches[1][0]["id"]
    ):
        text = (
            "Your question may relate to more than one topic in my knowledge base "
            f"(**{matches[0][0]['title']}** or **{matches[1][0]['title']}**).\n\n"
            f"{primary['clarifying_question']}\n\n"
            "Reply with a few more facts so I can use the curated entry that fits."
        )
        return LegalAnswer("clarify", text, topic_id=primary["id"], score=score)

    if score >= MATCH_MIN_SCORE:
        body = _format_topic_answer(primary)
        if len(matches) > 1 and matches[1][1] >= MATCH_MIN_SCORE:
            related = ", ".join(t["title"] for t, _ in matches[1:3])
            body += f"\n\n**You may also want to explore:** {related}"
        body += (
            "\n\n*(Response generated by LawyerAI's local legal information engine, "
            "not a live cloud AI model.)*"
        )
        return LegalAnswer("matched", body, topic_id=primary["id"], score=score)

    if score >= CLARIFY_MIN_SCORE:
        return LegalAnswer(
            "clarify",
            _clarifying_response(primary, original),
            topic_id=primary["id"],
            score=score,
        )

    return LegalAnswer(
        "unknown",
        _unknown_response(original, matches),
        score=score,
    )


def answer_legal_question(
    message: str,
    recent_user_messages: list[str] | None = None,
) -> str:
    """Backward-compatible string answer from the local engine only."""
    return resolve_legal_question(message, recent_user_messages).text
