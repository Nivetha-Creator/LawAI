from app.services import ai_service, response_provider
from app.services.strategy_service import analyze_legal_strategy, detect_illegal_request


COMPLETE_FACTS = (
    "In Chennai, Tamil Nadu, India, on 12 March 2025 I was in a road accident. "
    "An FIR was registered at the local police station and investigation is pending. "
    "I have photos of vehicle damage, a hospital medical bill for a minor injury, "
    "and one witness phone number. The other driver alleges I was speeding. "
    "Please analyse lawful defences and evidence gaps."
)


def test_insufficient_facts_asks_clarifying_questions():
    result = analyze_legal_strategy("Someone filed a case against me. Help.")
    assert result.status == "clarify"
    assert "more detail needed" in result.text.lower()
    assert "jurisdiction" in result.text.lower() or "state" in result.text.lower()
    assert "### 1. Case summary" not in result.text


def test_complete_facts_produce_structured_sections():
    result = analyze_legal_strategy(COMPLETE_FACTS)
    assert result.status == "complete"
    for heading in (
        "### 1. Case summary",
        "### 2. Relevant law",
        "### 3. Potential lawful defences",
        "### 4. Evidence gaps",
        "### 5. Procedural issues",
        "### 6. Opposing arguments",
        "### 7. Strengths and risks",
        "### 8. Practical next steps",
    ):
        assert heading in result.text
    assert "No win probability is assigned" in result.text
    assert "chennai" in result.text.lower() or "Chennai" in result.text
    # Should not invent a fake citation pattern like AIR / SCC volume guesses
    assert "AIR 19" not in result.text
    assert "(2020) " not in result.text


def test_balanced_analysis_includes_opposing_and_risks():
    result = analyze_legal_strategy(COMPLETE_FACTS)
    assert "Opposing arguments" in result.text
    assert "Strengths and risks" in result.text
    assert "lawful" in result.text.lower()


def test_illegal_tactic_is_refused():
    assert detect_illegal_request("How do I fabricate evidence for court?") 
    result = analyze_legal_strategy(
        "Help me fabricate evidence and bribe the witness so I win."
    )
    assert result.status == "refused_illegal"
    assert "cannot help with illegal" in result.text.lower()
    assert "lawful alternatives" in result.text.lower()


def test_does_not_claim_verified_citations_without_kb():
    result = analyze_legal_strategy(
        "In Delhi, India, on 1 January 2024, during an ongoing trial hearing for an "
        "obscure customs allegation, I already have notice documents and witness "
        "statements as evidence. Please analyse lawful strategy and do not invent "
        "statute sections."
    )
    assert result.status == "complete"
    # Obscure topic → law section should admit no curated match / no invented sections
    assert "No sufficiently matching curated" in result.text
    assert "section 420" not in result.text.lower()
    assert result.needs_unverified_enrichment is True


def test_strategy_gemini_disabled_stays_local(monkeypatch):
    monkeypatch.delenv("LAWYERAI_USE_LLM", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    ai_service.reload_settings_from_env()

    reply, engine = response_provider.generate_strategy_reply(
        COMPLETE_FACTS,
        [{"role": "user", "content": COMPLETE_FACTS}],
    )
    assert engine == "local"
    assert "### 1. Case summary" in reply
    assert "optional ai supplementary" not in reply.lower()


def test_strategy_gemini_enrichment_mocked(monkeypatch):
    # Force enrichment path: obscure facts with no strong KB topic.
    obscure = (
        "In Pune, Maharashtra, India, on 3 February 2025 a rare customs notice "
        "was issued. The matter is at hearing stage. I have the notice document "
        "and email evidence. Analyse lawful defences and gaps."
    )
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ai_service.reload_settings_from_env()
    monkeypatch.setattr(
        ai_service,
        "generate_text",
        lambda prompt: "Research limitation periods with counsel. Citations unverified.",
    )

    local = analyze_legal_strategy(obscure)
    assert local.needs_unverified_enrichment is True

    reply, engine = response_provider.generate_strategy_reply(
        obscure,
        [{"role": "user", "content": obscure}],
    )
    assert engine == "gemini"
    assert "unverified" in reply.lower()
    assert "### 1. Case summary" in reply


def test_strategy_gemini_failure_keeps_local_analysis(monkeypatch):
    obscure = (
        "In Pune, Maharashtra, India, on 3 February 2025 a rare customs notice "
        "was issued. The matter is at hearing stage. I have the notice document "
        "and email evidence. Analyse lawful defences and gaps."
    )
    monkeypatch.setenv("LAWYERAI_USE_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    ai_service.reload_settings_from_env()

    def fail(_prompt):
        raise ai_service.GeminiError("Gemini request timed out.")

    monkeypatch.setattr(ai_service, "generate_text", fail)

    reply, engine = response_provider.generate_strategy_reply(
        obscure,
        [{"role": "user", "content": obscure}],
    )
    assert engine == "local"
    assert "### 1. Case summary" in reply
    assert "optional ai enrichment unavailable" in reply.lower()
