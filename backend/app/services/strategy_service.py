"""
Legal Strategy Analysis (lawful defences, evidence gaps, procedure).

Interprets "loopholes" as lawful arguments and procedural/evidentiary
weaknesses — never illegal tactics. Local-first; does not invent citations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from app.knowledge.topics import LEGAL_TOPICS
from app.llm.types import GenerationRequest
from app.services.legal_service import match_topics, normalize_query

OFFICIAL_SOURCE = "https://www.indiacode.nic.in/"

StrategyStatus = Literal["clarify", "complete", "refused_illegal"]

ILLEGAL_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(fake|fabricat\w*|forge\w*)\b.{0,40}\bevidence\b", re.I), "fabricating evidence"),
    (re.compile(r"\bdestroy\w*\b.{0,30}\bevidence\b", re.I), "destroying evidence"),
    (re.compile(r"\blie\b.{0,30}\b(oath|court|police)\b", re.I), "lying under oath / to authorities"),
    (re.compile(r"\b(bribe|bribery|pay\s+off)\b", re.I), "bribery"),
    (re.compile(r"\b(intimidate|threaten|threat)\b.{0,40}\bwitness", re.I), "intimidating witnesses"),
    (re.compile(r"\bconceal\w*\b.{0,30}\bevidence\b", re.I), "concealing evidence"),
    (re.compile(r"\bevade\b.{0,30}\b(summons|warrant|arrest|process)\b", re.I), "evading lawful process"),
    (re.compile(r"\bhow\s+to\s+(get\s+away|escape)\b.{0,40}\b(crime|police)\b", re.I), "evading lawful process"),
)

FACT_CHECKS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "jurisdiction",
        ("india", "indian", "state", "delhi", "mumbai", "chennai", "tamil nadu",
         "karnataka", "maharashtra", "kerala", "telangana", "andhra", "gujarat",
         "rajasthan", "punjab", "haryana", "west bengal", "kolkata", "hyderabad",
         "bangalore", "bengaluru", "pune", "jurisdiction", "district"),
        "Which state/city (or confirm India) is the matter in?",
    ),
    (
        "date_or_timing",
        ("2020", "2021", "2022", "2023", "2024", "2025", "2026", "yesterday",
         "last week", "last month", "today", "january", "february", "march",
         "april", "may", "june", "july", "august", "september", "october",
         "november", "december", "date", "on ", "ago", "morning", "night"),
        "When did the incident occur (approximate date), and what stage are you at now?",
    ),
    (
        "allegations",
        ("accuse", "alleg", "charge", "fir", "complaint", "offence", "offense",
         "theft", "assault", "accident", "fraud", "cheque", "dowry", "bail",
         "arrest", "notice", "claim", "damage", "injury", "hit and run",
         "insurance", "dispute", "case against", "police"),
        "What are you accused of, or what claim/complaint are you facing or making?",
    ),
    (
        "procedural_stage",
        ("fir", "investigation", "charge sheet", "chargesheet", "trial",
         "hearing", "bail", "notice", "summons", "arrest", "remand",
         "mediation", "consumer", "court", "police station", "filed",
         "pending", "appealed", "stage"),
        "What is the current stage (police complaint, investigation, bail, trial, civil claim, etc.)?",
    ),
    (
        "evidence",
        ("evidence", "witness", "cctv", "video", "photo", "document", "message",
         "whatsapp", "receipt", "bill", "medical", "report", "recording",
         "dashcam", "proof", "statement", "chat", "email", "invoice"),
        "What evidence do you already have (or know exists), and what is missing?",
    ),
)


@dataclass
class StrategyResult:
    status: StrategyStatus
    text: str
    missing_fields: list[str] = field(default_factory=list)
    topic_ids: list[str] = field(default_factory=list)
    needs_unverified_enrichment: bool = False


def detect_illegal_request(text: str) -> str | None:
    for pattern, label in ILLEGAL_PATTERNS:
        if pattern.search(text or ""):
            return label
    return None


def assess_fact_coverage(combined: str) -> tuple[list[str], list[str], list[str]]:
    """Return (present_fields, missing_fields, clarifying_questions)."""
    normalized = normalize_query(combined)
    present: list[str] = []
    missing: list[str] = []
    questions: list[str] = []

    for field_id, cues, question in FACT_CHECKS:
        if any(cue in normalized for cue in cues):
            present.append(field_id)
        else:
            missing.append(field_id)
            questions.append(question)

    return present, missing, questions


def _refuse_illegal(label: str) -> StrategyResult:
    text = (
        "**I cannot help with illegal tactics.**\n\n"
        f"Your request appears to ask about **{label}**. LawyerAI will not advise "
        "fabricating or destroying evidence, lying under oath, intimidating witnesses, "
        "bribery, concealing relevant evidence, or evading lawful process.\n\n"
        "**Lawful alternatives instead**\n"
        "- Preserve existing evidence and obtain copies of records through proper channels\n"
        "- Identify genuine weaknesses in the other side’s proof (gaps, authenticity, chain of custody)\n"
        "- Raise procedural safeguards and fair-process issues with a qualified advocate\n"
        "- Prepare an honest factual timeline for your lawyer\n\n"
        "If you restate your situation without asking for illegal methods, I can run a "
        "**Legal Strategy Analysis** focused on lawful defences and evidence issues.\n\n"
        f"Official legislation: {OFFICIAL_SOURCE}"
    )
    return StrategyResult("refused_illegal", text)


def _clarifying_response(
    user_text: str,
    missing: list[str],
    questions: list[str],
    present: list[str],
) -> StrategyResult:
    lines = [
        "**Legal Strategy Analysis — more detail needed**",
        "",
        "I will not invent facts, statute sections, or case outcomes. "
        "Please avoid sharing unnecessary personal identifiers (full Aadhaar, "
        "passwords, or confidential case files) unless you choose to.",
        "",
        f"**What I already see signals for:** {', '.join(present) if present else 'limited context only'}",
        "",
        "**Please answer the missing points:**",
    ]
    for q in questions[:5]:
        lines.append(f"- {q}")
    lines.extend(
        [
            "",
            "**Your description so far:**",
            user_text[:800],
            "",
            "Reply in one message covering jurisdiction, approximate dates, "
            "allegations, procedural stage, and available evidence.",
        ]
    )
    return StrategyResult("clarify", "\n".join(lines), missing_fields=missing)


def _strength_label(kind: str) -> str:
    return {
        "strong": "Stronger (on stated facts)",
        "plausible": "Plausible (needs support)",
        "weak": "Weak / fragile",
        "unassessed": "Unassessed (facts missing)",
    }.get(kind, kind)


def build_structured_analysis(
    user_text: str,
    present: list[str],
    missing: list[str],
) -> StrategyResult:
    matches = match_topics(user_text, limit=3)
    strong_topics = [(t, s) for t, s in matches if s >= 3.0]
    topic_ids = [t["id"] for t, _ in strong_topics]

    # --- 1 Case summary ---
    summary = (
        "Based only on what you wrote (no assumed extras):\n"
        f"> {user_text.strip()[:1200]}"
    )

    # --- 2 Relevant law ---
    if strong_topics:
        law_lines = [
            "Potentially related **curated** topics from LawyerAI’s knowledge base "
            "(general information — not a confirmation that these statutes apply to you):"
        ]
        for topic, score in strong_topics:
            law_lines.append(f"- **{topic['title']}** — {topic['summary'][:280]}…")
        law_lines.append(
            f"\nVerify primary texts on {OFFICIAL_SOURCE}. "
            "Consider the incident date and any transitional rules (for example "
            "pre/post July 2024 criminal-law framework) with a qualified advocate. "
            "**No specific section numbers are invented here.**"
        )
        law_section = "\n".join(law_lines)
        needs_enrichment = False
    else:
        law_section = (
            "No sufficiently matching curated knowledge-base topic was found for "
            "your facts. **I will not invent statute sections, case names, or URLs.** "
            f"Check {OFFICIAL_SOURCE} and consult an advocate. "
            "If optional Gemini fallback is enabled, an unverified AI note may appear below."
        )
        needs_enrichment = True

    # --- 3 Lawful defences ---
    defences: list[str] = []
    normalized = normalize_query(user_text)
    if any(k in normalized for k in ("alibi", "not present", "was not there", "elsewhere")):
        defences.append(
            f"{_strength_label('plausible')}: Presence/identity challenge — only if supported by "
            "independent evidence you can produce."
        )
    if any(k in normalized for k in ("consent", "permission", "agreed")):
        defences.append(
            f"{_strength_label('plausible')}: Consent / authorisation narrative — assess "
            "credibility and documents carefully with counsel."
        )
    if any(k in normalized for k in ("self defence", "self-defense", "private defence")):
        defences.append(
            f"{_strength_label('plausible')}: Private defence / proportionate force themes — "
            "highly fact-specific; do not overclaim."
        )
    if any(k in normalized for k in ("accident", "negligence", "no intent", "mistake")):
        defences.append(
            f"{_strength_label('plausible')}: Mental element / accident vs intention — "
            "depends on evidence of conduct and surrounding circumstances."
        )
    if any(k in normalized for k in ("cctv", "video", "footage")):
        defences.append(
            f"{_strength_label('plausible')}: Challenge authenticity, continuity, or "
            "completeness of video evidence rather than inventing counter-footage."
        )
    if any(k in normalized for k in ("insurance", "surveyor", "claim")):
        defences.append(
            f"{_strength_label('plausible')}: Policy terms, survey process, and documentation "
            "timeline arguments in an insurance dispute."
        )
    if not defences:
        defences.append(
            f"{_strength_label('unassessed')}: Specific lawful defences need clearer "
            "allegations and evidence list from you or your advocate."
        )

    # --- 4 Evidence gaps ---
    gaps = [
        "List each allegation element and mark evidence as: available / missing / disputed.",
        "Note whether witness statements are independent or interested parties.",
        "Flag digital evidence lacking original device, metadata, or chain-of-custody notes.",
    ]
    if "evidence" in missing:
        gaps.insert(
            0,
            f"{_strength_label('unassessed')}: You have not yet described available evidence.",
        )
    if any(k in normalized for k in ("no witness", "no cctv", "no proof", "only my word")):
        gaps.append(
            f"{_strength_label('weak')}: Heavy reliance on uncorroborated oral account — "
            "seek contemporaneous records where lawful."
        )

    # --- 5 Procedural issues ---
    procedural = [
        "Ask counsel whether required notices, timelines, or hearing rights were observed.",
        "Keep copies of every police/court/insurer communication and acknowledgement.",
        "Do not ignore summons or hearing dates; seek adjournment through proper channels if needed.",
    ]
    if any(k in normalized for k in ("fir", "police", "arrest", "bail")):
        procedural.append(
            "For criminal process: clarify custody status, bail conditions, and what "
            "documents you were given (without inventing section labels)."
        )
    if "2024" in normalized or "2025" in normalized or "2026" in normalized:
        procedural.append(
            "Incident timing may affect whether older or newer criminal-procedure labels "
            "appear on papers — compare with India Code and ask your advocate."
        )

    # --- 6 Opposing arguments ---
    opposing = [
        "The other side may emphasise consistency of their narrative and any documentary trail.",
        "They may attack delay in reporting, gaps in your timeline, or missing corroboration.",
        "They may portray your explanation as after-the-fact reconstruction — prepare a dated chronology.",
    ]

    # --- 7 Strengths and risks ---
    strengths_risks = [
        f"**{_strength_label('strong')}:** Clear, dated facts you can document without contradiction.",
        f"**{_strength_label('plausible')}:** Defences listed above that match your narrative but need exhibits.",
        f"**{_strength_label('weak')}:** Arguments that require facts you have not supplied — do not present them as proven.",
        f"**{_strength_label('unassessed')}:** Legal characterisation (exact offence/claim label) until counsel reviews papers.",
        "**No win probability is assigned** — outcomes depend on evidence, forum, and advocacy.",
    ]

    # --- 8 Practical next steps ---
    steps = [
        "Write a neutral chronology (date → event → who was present → documents).",
        "Preserve phones/CCTV requests lawfully; do not alter original files.",
        "Obtain acknowledgements of complaints, claim numbers, and medical records.",
        "Prepare questions for a qualified Indian advocate; bring papers rather than uploading "
        "sensitive IDs into chat tools.",
        f"Cross-check legislation on {OFFICIAL_SOURCE}.",
    ]
    if missing:
        steps.insert(
            0,
            "Fill remaining gaps: " + ", ".join(missing) + ".",
        )

    body = "\n".join(
        [
            "**Legal Strategy Analysis** (educational; not legal advice)",
            "",
            "### 1. Case summary",
            summary,
            "",
            "### 2. Relevant law",
            law_section,
            "",
            "### 3. Potential lawful defences",
            *[f"- {d}" for d in defences],
            "",
            "### 4. Evidence gaps",
            *[f"- {g}" for g in gaps],
            "",
            "### 5. Procedural issues",
            *[f"- {p}" for p in procedural],
            "",
            "### 6. Opposing arguments",
            *[f"- {o}" for o in opposing],
            "",
            "### 7. Strengths and risks",
            *[f"- {s}" for s in strengths_risks],
            "",
            "### 8. Practical next steps",
            *[f"- {s}" for s in steps],
            "",
            "---",
            "*Local strategy engine: lawful analysis only. “Loopholes” here means "
            "procedural/evidentiary weaknesses and legitimate arguments — not illegal tactics. "
            "Verified legal rules appear only where linked to the curated knowledge base; "
            "other reasoning is structured guidance, not a court prediction.*",
        ]
    )

    return StrategyResult(
        status="complete",
        text=body,
        missing_fields=missing,
        topic_ids=topic_ids,
        needs_unverified_enrichment=needs_enrichment,
    )


def analyze_legal_strategy(
    message: str,
    recent_user_messages: list[str] | None = None,
) -> StrategyResult:
    original = (message or "").strip()
    combined = original
    if recent_user_messages:
        combined = " ".join(recent_user_messages[-3:] + [original])

    illegal = detect_illegal_request(combined)
    if illegal:
        return _refuse_illegal(illegal)

    present, missing, questions = assess_fact_coverage(combined)

    # Require enough substance + most fact dimensions (allow 1 missing if message is rich).
    word_count = len(re.findall(r"\w+", original))
    critical_missing = [m for m in missing if m in {"allegations", "evidence", "procedural_stage"}]

    if word_count < 25 or len(present) < 3 or len(critical_missing) >= 2:
        return _clarifying_response(original, missing, questions, present)

    return build_structured_analysis(original, present, missing)


STRATEGY_GEMINI_PROMPT = """
You assist LawyerAI's Legal Strategy mode for Indian law education.
You are NOT a lawyer. Do NOT invent statute section numbers, case names, quotations, or URLs.
Do NOT recommend illegal tactics. If unsure, say sources are unverified.
Comment only on lawful defences, evidence gaps, and procedure in general terms.
Keep the note under 250 words.
"""


def strategy_generation_request(
    user_text: str,
    local_analysis: str,
    evidence: str = "",
) -> GenerationRequest:
    """Neutral request. Empty evidence keeps the previous enrichment prompt."""
    evidence = (evidence or "").strip()
    if not evidence:
        return GenerationRequest(
            system_instruction=STRATEGY_GEMINI_PROMPT.strip(),
            user_prompt=(
                f"User facts:\n{user_text}\n\n"
                f"Local analysis already provided (do not contradict safety rules):\n"
                f"{local_analysis[:3000]}\n\n"
                "Add a short unverified supplementary note on possible legal themes to research "
                "with a lawyer. Explicitly state that citations are unverified."
            ),
        )
    return GenerationRequest(
        system_instruction=(
            STRATEGY_GEMINI_PROMPT.strip()
            + "\nCite only titles, sections, and URLs that appear in the retrieved evidence. "
            "https://www.indiacode.nic.in/ may be named as a general official source."
        ),
        user_prompt=(
            f"User facts:\n{user_text}\n\n"
            f"Local analysis already provided (do not contradict safety rules):\n"
            f"{local_analysis[:3000]}\n\n"
            f"Retrieved evidence:\n{evidence}\n\n"
            "Add a short note grounded in that evidence. Do not invent citations."
        ),
    )


def build_strategy_enrichment_prompt(user_text: str, local_analysis: str) -> str:
    request = strategy_generation_request(user_text, local_analysis)
    system = (request.system_instruction or "").strip()
    return f"{system}\n\n{request.user_prompt}"


def format_strategy_enrichment(raw: str) -> str:
    return (
        "\n\n### Optional AI supplementary note (unverified)\n"
        f"{raw.strip()}\n\n"
        "*Generated by optional Gemini fallback. This is **not** verified curated law "
        "and is **not** legal advice. Do not treat it as authoritative.*"
    )
