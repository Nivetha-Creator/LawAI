"""
Local educational debate partner and rule-based performance feedback.
"""

from __future__ import annotations

import re
from typing import Any

REASONING_MARKERS = (
    "because",
    "therefore",
    "thus",
    "hence",
    "since",
    "accordingly",
    "consequently",
    "as a result",
    "due to",
    "given that",
)

COUNTER_MARKERS = (
    "however",
    "although",
    "nevertheless",
    "on the other hand",
    "contrary",
    "rebut",
    "dispute",
    "challenge",
    "undermines",
    "weakens",
)

EVIDENCE_MARKERS = (
    "evidence",
    "witness",
    "document",
    "cctv",
    "forensic",
    "record",
    "proof",
    "exhibit",
    "testimony",
    "circumstantial",
)

DEBATE_TOPIC_HINTS: dict[str, tuple[str, ...]] = {
    "cctv": (
        "cctv",
        "footage",
        "video",
        "surveillance",
        "camera",
    ),
    "bail": ("bail", "custody", "arrest", "liberty"),
    "intent": ("intent", "mens rea", "motive", "premeditation"),
    "self_defence": ("self defence", "self-defense", "private defence"),
    "default": ("legal", "case", "court", "trial", "argument"),
}

OPPOSING_OPENERS = {
    "Prosecution": (
        "From the prosecution perspective, the core issue is whether the facts you "
        "describe meet the elements the law requires and whether the evidence would "
        "be admissible and credible.",
        "The prosecution would stress consistency in the narrative, corroboration, "
        "and any gaps in the defence explanation.",
    ),
    "Defence": (
        "From the defence perspective, the focus is on whether the prosecution's "
        "story is complete, whether alternative explanations exist, and whether "
        "procedural safeguards were followed.",
        "The defence would highlight missing links in the chain of proof and reasonable doubt.",
    ),
}

FOLLOW_UP_QUESTIONS = {
    "cctv": (
        "How would you address chain-of-custody or authenticity concerns about the footage?",
        "What independent evidence supports your position if the video is challenged?",
    ),
    "bail": (
        "What concrete factors show the accused will not abscond or influence witnesses?",
        "How do you respond to the seriousness of the allegations?",
    ),
    "intent": (
        "Which facts directly show state of mind rather than mere outcome?",
        "How do you distinguish accident or negligence from intentional conduct?",
    ),
    "self_defence": (
        "Was the force proportionate to the threat as you describe it?",
        "Was retreat or lesser force reasonably available?",
    ),
    "default": (
        "What is the weakest point in your argument, and how do you answer it?",
        "Which fact, if disproved, would change your position?",
    ),
}


def detect_debate_theme(topic: str, text: str) -> str:
    blob = f"{topic} {text}".lower()
    for theme, keywords in DEBATE_TOPIC_HINTS.items():
        if theme == "default":
            continue
        if any(k in blob for k in keywords):
            return theme
    return "default"


def _pick_question(theme: str, turn_index: int) -> str:
    options = FOLLOW_UP_QUESTIONS.get(theme, FOLLOW_UP_QUESTIONS["default"])
    return options[turn_index % len(options)]


def _extract_user_messages(transcript: list[dict[str, Any]]) -> list[str]:
    return [
        item["content"].strip()
        for item in transcript
        if item.get("role") == "user" and item.get("content", "").strip()
    ]


def generate_debate_reply(
    user_side: str,
    topic: str,
    user_message: str,
    transcript: list[dict[str, Any]],
) -> str:
    opposing = "Defence" if user_side == "Prosecution" else "Prosecution"
    theme = detect_debate_theme(topic, f"{topic} {user_message}")
    user_turns = _extract_user_messages(transcript)
    turn_index = max(0, len(user_turns) - 1)

    opener = OPPOSING_OPENERS[opposing][turn_index % len(OPPOSING_OPENERS[opposing])]
    question = _pick_question(theme, turn_index)

    quoted = user_message.strip()
    if len(quoted) > 400:
        quoted = quoted[:400] + "…"

    lines = [
        f"**Opposing counsel ({opposing}) — educational simulation**",
        "",
        f"Topic: {topic.strip() or 'General legal debate'}",
        "",
        opener,
        "",
        f"On your latest point — \"{quoted}\" — I would press that the {opposing.lower()} "
        f"view still needs stronger support on facts and reasoning before a court would accept it.",
        "",
        f"**Follow-up:** {question}",
        "",
        "*(Local debate engine — not a prediction of court results or legal advice.)*",
    ]
    return "\n".join(lines)


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    lower = text.lower()
    return sum(1 for m in markers if m in lower)


def _score_dimension(value: float, low: float, high: float) -> int:
    if value <= low:
        return 3
    if value <= (low + high) / 2:
        return 6
    if value <= high:
        return 8
    return 10


def generate_debate_feedback(
    transcript: list[dict[str, Any]],
    user_side: str,
    topic: str,
) -> str:
    user_messages = _extract_user_messages(transcript)
    if not user_messages:
        return (
            "There are not enough of your messages to review. Send at least one "
            "argument before ending the debate."
        )

    combined = " ".join(user_messages)
    words = re.findall(r"\w+", combined)
    word_count = len(words)
    sentence_count = max(1, len(re.split(r"[.!?]+", combined)))

    topic_tokens = set(re.findall(r"[a-z0-9]+", topic.lower()))
    message_tokens = set(w.lower() for w in words)
    topic_overlap = len(topic_tokens & message_tokens) if topic_tokens else 0

    reasoning_hits = _count_markers(combined, REASONING_MARKERS)
    counter_hits = _count_markers(combined, COUNTER_MARKERS)
    evidence_hits = _count_markers(combined, EVIDENCE_MARKERS)
    questions_asked = combined.count("?")

    relevance = _score_dimension(topic_overlap + (2 if topic.lower() in combined.lower() else 0), 0, 4)
    clarity = _score_dimension(sentence_count / max(1, len(user_messages)), 1, 4)
    reasoning = _score_dimension(reasoning_hits, 0, 3)
    counter = _score_dimension(counter_hits, 0, 2)
    evidence = _score_dimension(evidence_hits, 0, 2)
    responsiveness = _score_dimension(questions_asked + len(user_messages), 1, 5)

    scores = {
        "Relevance to topic": relevance,
        "Clarity (structure)": clarity,
        "Reasoning indicators": reasoning,
        "Counterargument language": counter,
        "Evidence references": evidence,
        "Engagement / responsiveness": responsiveness,
    }

    strengths: list[str] = []
    improvements: list[str] = []

    if word_count >= 40:
        strengths.append("You provided substantive detail across your turns.")
    else:
        improvements.append("Expand key points with more factual detail (aim for fuller paragraphs).")

    if reasoning_hits >= 2:
        strengths.append("You used causal or logical connectors (e.g. because, therefore).")
    else:
        improvements.append("Link facts to conclusions explicitly using because/therefore language.")

    if evidence_hits >= 1:
        strengths.append("You referenced evidence or proof concepts.")
    else:
        improvements.append("Name the evidence you would rely on (documents, witnesses, records).")

    if counter_hits >= 1:
        strengths.append("You engaged with opposing viewpoints.")
    else:
        improvements.append("Preempt one counterargument and answer it in your next practice round.")

    if topic_overlap < 2 and topic.strip():
        improvements.append("Tie each paragraph back to the debate topic keywords.")

    avg = sum(scores.values()) / len(scores)

    lines = [
        "**Debate practice feedback (rule-based, not AI grading)**",
        "",
        f"Side practised: **{user_side}**",
        f"Topic: **{topic.strip() or 'Not recorded'}**",
        f"Your messages analysed: **{len(user_messages)}** (~{word_count} words)",
        "",
        "**Scores (1–10, heuristic checklist)**",
    ]
    for label, value in scores.items():
        lines.append(f"- {label}: {value}/10")

    lines.extend(
        [
            "",
            f"**Overall checklist average:** {avg:.1f}/10 (educational only; not a court or exam result)",
            "",
            "**Strengths**",
        ]
    )
    lines.extend(f"- {s}" for s in strengths) if strengths else lines.append("- Keep practising — early attempt.")

    lines.append("")
    lines.append("**Improvements**")
    lines.extend(f"- {i}" for i in improvements)

    lines.extend(
        [
            "",
            "**Practice exercise**",
            "Draft a two-minute closing statement that (1) states your theory of the case, "
            "(2) cites two types of evidence you would use, and (3) answers one weakness "
            "the other side raised in this session.",
            "",
            "*(Generated by LawyerAI's local debate feedback rules, not an advanced AI assessment.)*",
        ]
    )
    return "\n".join(lines)
