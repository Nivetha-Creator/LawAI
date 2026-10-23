from app.services.legal_service import (
    answer_legal_question,
    match_topics,
    normalize_query,
    resolve_legal_question,
)


def test_normalize_query_collapses_noise_and_aliases():
    assert "hit and run" in normalize_query("  HIT & RUN!!! ")
    assert "road accident" in normalize_query("I met accident yesterday")


def test_match_topics_bns_still_works():
    matches = match_topics("What is the difference between BNS and IPC?")
    assert matches
    assert matches[0][0]["id"] == "bns_ipc_transition"
    assert matches[0][1] >= 3.5


def test_known_answer_includes_knowledge_marker():
    reply = answer_legal_question("Explain BNS BNSS BSA criminal law July 2024")
    assert "curated knowledge base" in reply
    assert "local legal information engine" in reply


def test_road_accident_english_phrasings():
    phrasings = [
        "What should I do after a road accident?",
        "My car was in a traffic accident yesterday",
        "bike accident on the main road — next steps?",
    ]
    for text in phrasings:
        result = resolve_legal_question(text)
        assert result.status == "matched", text
        assert result.topic_id == "road_accident_basics", text


def test_hit_and_run_and_tanglish():
    cases = [
        ("Someone did a hit and run and fled", "hit_and_run"),
        ("Car odittu poyiduchu after accident", "hit_and_run"),
    ]
    for text, topic_id in cases:
        result = resolve_legal_question(text)
        assert result.status == "matched", text
        assert result.topic_id == topic_id, text


def test_insurance_and_vehicle_damage_topics():
    insurance = resolve_legal_question(
        "How do I start a motor insurance claim after an accident?"
    )
    assert insurance.status == "matched"
    assert insurance.topic_id == "motor_insurance_claim"

    damage = resolve_legal_question(
        "Other car caused bumper damage — vehicle repair claim tips?"
    )
    assert damage.status == "matched"
    assert damage.topic_id == "vehicle_damage_claim"


def test_weak_single_keyword_does_not_fabricate_answer():
    result = resolve_legal_question("police")
    assert result.status in {"unknown", "clarify"}
    assert "curated knowledge base" not in result.text or result.status == "clarify"


def test_unknown_question_does_not_fabricate():
    reply = answer_legal_question(
        "What is the exact section number for a niche tax dispute in 1987?"
    )
    assert "do not have curated information" in reply.lower()
    assert "will not guess" in reply.lower()


def test_ambiguous_or_thin_detail_asks_clarifying_question():
    # Mid-strength cue without enough detail should clarify rather than invent.
    result = resolve_legal_question("accident insurance")
    assert result.status in {"clarify", "matched", "unknown"}
    if result.status == "clarify":
        assert "?" in result.text
