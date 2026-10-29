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

COURTROOM_HINTS = (
    "cctv",
    "footage",
    "witness",
    "accused",
    "bail",
    "trial",
    "conviction",
    "evidence",
    "exhibit",
    "mens rea",
    "self-defence",
    "self defense",
    "arrest",
    "alibi",
    "chain of custody",
)

THEME_COUNTERS: dict[str, dict[str, tuple[str, ...]]] = {
    "cctv": {
        "Prosecution": (
            "A recording can still corroborate time, place, and identity even if it is not a confession of intent.",
            "Challenges to authenticity go to weight when the recording process can be explained; they do not automatically erase what the images show.",
        ),
        "Defence": (
            "A clip does not speak for itself: identification, editing, and missing off-camera events can each raise reasonable doubt.",
            "Without a clean chain of custody, the footage is an incomplete account, not a closed case.",
        ),
    },
    "bail": {
        "Prosecution": (
            "The seriousness of the allegation and the risk of interference with witnesses can outweigh a bare assurance that the accused will appear.",
            "Liberty is important, but conditions only work if the person is likely to obey them; unexplained absconding risk still supports custody arguments.",
        ),
        "Defence": (
            "Custody is the exception: without concrete flight or tampering facts, the case for release on conditions remains stronger than continued detention.",
            "The allegation’s gravity is not proof. Ties to family, work, and the jurisdiction still support bail unless specific risks are shown.",
        ),
    },
    "intent": {
        "Prosecution": (
            "State of mind is often inferred from conduct, timing, and what the person did immediately after the event—not only from a confession.",
            "Calling the outcome an accident does not explain choices that look planned, targeted, or concealed.",
        ),
        "Defence": (
            "An outcome is not mens rea. If accident, negligence, or another purpose fits the same facts, intent has not been proved.",
            "Without facts that uniquely show purpose, the prosecution is asking a decision-maker to guess at state of mind.",
        ),
    },
    "self_defence": {
        "Prosecution": (
            "Private defence fails if the force used went beyond the threat as it then appeared, or if a clearly safer option was ignored.",
            "A claim of defence still has to fit the sequence: who started the confrontation, and whether the response was proportionate.",
        ),
        "Defence": (
            "The question is how the threat appeared at the time, not how it looks in hindsight after the danger had passed.",
            "If the other side was the aggressor, requiring perfect calm or retreat can overstate what the law expects in the moment.",
        ),
    },
}

# Keyword-triggered counters so the reply actually meets the user's last point.
# Both strings are counters to the user's claim; the wording follows the bot's assigned side.
CLAIM_COUNTERS: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (
        ("irreversible", "cannot be undone", "wrongful conviction", "innocent"),
        "Error risk is a reason for appeals and clemency, not by itself proof that your conclusion follows.",
        "I do not concede the point: irreversibility is a reason for careful review, not a reason to treat your last sentence as decisive.",
    ),
    (
        ("death penalty", "capital punishment", "state should not kill", "execute"),
        "The most serious offences are still treated as uniquely grave; a rare, reviewed penalty is not answered merely by rejecting it in principle.",
        "Calling the sanction illegitimate does not explain why a lawful, tightly limited penalty cannot remain part of the framework you want to dismantle.",
    ),
    (
        ("unequal", "poor", "poverty", "worse counsel", "discrimination"),
        "Uneven practice is a reason to improve process and legal aid, not automatically a reason to abandon the rule you are attacking.",
        "Inequality in counsel is a process defect to fix; it does not, by itself, establish that your preferred outcome is the only fair one.",
    ),
    (
        ("deterrence", "deter"),
        "Even contested deterrence research does not erase a preventive or denunciatory role for a serious sanction alongside rehabilitation.",
        "Saying deterrence is unproven does not show that your alternative actually prevents the harm; that still has to be argued, not assumed.",
    ),
    (
        ("privacy", "surveillance", "camera"),
        "Privacy concerns go to how recordings are obtained and used; they do not by themselves make every recording irrelevant to a disputed fact.",
        "A privacy objection does not decide reliability on these facts; you still have to show why this recording cannot be used as you claim.",
    ),
    (
        ("reasonable doubt", "burden", "must prove"),
        "Accepting the burden does not mean every gap you name is a reasonable doubt; some gaps are speculation unless tied to the evidence.",
        "Pointing to the burden is not a substitute for an alternative account of the facts you already accept.",
    ),
    (
        ("contract", "rent", "tenant", "landlord", "policy"),
        "A fairness objection does not erase written terms the other party can still rely on; change should come through the agreement or the legal route that alters it.",
        "Repeating that a contract or policy exists is not an answer if you have not shown why those terms control the issue you just raised.",
    ),
)

GENERIC_COUNTERS = {
    "Prosecution": (
        "That point does not settle the issue. A counter is that the same facts can be read as supporting accountability, and the gaps you mention can be tested rather than assumed to defeat the case.",
        "Even granting part of what you said, you have not shown why the opposite conclusion must follow. The remaining facts still need an answer, not a concession.",
        "I take the other side: concern about risk or unfairness is a reason to tighten proof, not a reason to treat your last claim as the last word.",
    ),
    "Defence": (
        "I disagree that this is decisive. The counter is that a lawful alternative reading of the same facts is still open, and the other side has not closed it.",
        "Your last point still leaves a less drastic explanation on the table. Until that is excluded with specific proof, the opposing case is not made out.",
        "The objection stands: repeating the conclusion does not supply the missing link. Doubt, another cause, or a narrower remedy still has to be answered.",
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
        "What workable alternative do you offer if your last reason is only partly true?",
        "How do you answer the cost of the rule you want instead?",
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


def _pick_question(theme: str, turn_index: int, used: str = "") -> str:
    options = FOLLOW_UP_QUESTIONS.get(theme, FOLLOW_UP_QUESTIONS["default"])
    unused = [item for item in options if item.lower() not in used]
    if not unused:
        unused = list(FOLLOW_UP_QUESTIONS["default"])
        unused = [item for item in unused if item.lower() not in used] or unused
    return unused[turn_index % len(unused)]


def _extract_user_messages(transcript: list[dict[str, Any]]) -> list[str]:
    return [
        item["content"].strip()
        for item in transcript
        if item.get("role") == "user" and item.get("content", "").strip()
    ]


def _extract_assistant_messages(transcript: list[dict[str, Any]]) -> list[str]:
    return [
        item["content"].strip()
        for item in transcript
        if item.get("role") == "assistant" and item.get("content", "").strip()
    ]


def _is_courtroom_topic(topic: str, text: str) -> bool:
    topic_blob = (topic or "").lower()
    if detect_debate_theme(topic, topic_blob) != "default":
        return True
    if any(hint in topic_blob for hint in COURTROOM_HINTS):
        return True
    if not topic_blob.strip():
        return detect_debate_theme("", text) != "default"
    return False


def _user_claims(user_message: str) -> list[str]:
    text = re.sub(r"\s+", " ", (user_message or "").strip())
    parts = re.split(r"(?<=[.!?])\s+|\bbecause\b|\btherefore\b", text, flags=re.I)
    claims = [p.strip(" ,;:-") for p in parts if p and len(p.strip()) > 12]
    if not claims:
        claims = [text[:240] or "your last argument"]
    return claims[:2]


def _unused(options: tuple[str, ...] | list[str], used: str, turn_index: int) -> str:
    leftover = [item for item in options if item[:48].lower() not in used]
    pool = leftover or list(options)
    return pool[turn_index % len(pool)]


def _counter_for_claim(
    claim: str,
    opposing: str,
    theme: str,
    used: str,
    turn_index: int,
) -> str:
    lower = claim.lower()
    for keywords, prosecution, defence in CLAIM_COUNTERS:
        if any(key in lower for key in keywords):
            text = prosecution if opposing == "Prosecution" else defence
            if text[:48].lower() not in used:
                clipped = claim.strip().rstrip(".").strip()
                return f'On your point that "{clipped}": {text}'

    theme_options = THEME_COUNTERS.get(theme, {}).get(opposing)
    if theme_options:
        specific = _unused(theme_options, used, turn_index)
        clipped = claim.strip().rstrip(".").strip()
        return f'On your point that "{clipped}": {specific}'

    generic = _unused(GENERIC_COUNTERS[opposing], used, turn_index)
    clipped = claim.strip().rstrip(".").strip()
    return f'On your point that "{clipped}": {generic}'


def generate_debate_reply(
    user_side: str,
    topic: str,
    user_message: str,
    transcript: list[dict[str, Any]],
) -> str:
    opposing = "Defence" if user_side == "Prosecution" else "Prosecution"
    theme = detect_debate_theme(topic, f"{topic} {user_message}")
    courtroom = _is_courtroom_topic(topic, user_message)
    user_turns = _extract_user_messages(transcript)
    turn_index = max(0, len(user_turns) - 1)
    used = " ".join(_extract_assistant_messages(transcript)).lower()

    claims = _user_claims(user_message)
    counters: list[str] = []
    for index, claim in enumerate(claims):
        counters.append(
            _counter_for_claim(claim, opposing, theme, used + " ".join(counters).lower(), turn_index + index)
        )

    question = _pick_question(theme, turn_index, used)

    if courtroom:
        heading = f"**Opposing counsel ({opposing}) — educational simulation**"
        stance = (
            f"I am arguing as {opposing} against your last submission, not interviewing you."
            if turn_index == 0
            else f"Continuing as {opposing}, I meet that submission rather than restating a generic case theory."
        )
    else:
        heading = f"**Opposing side ({opposing}) — educational debate**"
        stance = (
            f"Assigned side: **{opposing}**. I will contest your position on this legal or policy question."
            if turn_index == 0
            else f"Still arguing as {opposing}: your latest reason does not close the debate."
        )

    lines = [
        heading,
        "",
        f"Topic: {topic.strip() or 'General legal debate'}",
        "",
        stance,
        "",
        *counters,
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
