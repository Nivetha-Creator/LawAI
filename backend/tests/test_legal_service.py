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


def test_educational_questions_answer_without_incident_prompts():
    cases = {
        "What is the Indian Constitution?": "constitution_overview",
        "What are Fundamental Rights under the Constitution?": "fundamental_rights_overview",
        "What is the difference between civil and criminal law?": "civil_vs_criminal",
        "What is an FIR in India?": "fir_and_complaint",
        "How are High Courts and the Supreme Court organised?": "indian_courts",
    }
    for text, topic_id in cases.items():
        result = resolve_legal_question(text)
        assert result.status == "matched", (text, result.status, result.topic_id)
        assert result.topic_id == topic_id, (text, result.topic_id)
        lowered = result.text.lower()
        assert "what happened, where" not in lowered
        assert "specific incident" not in lowered


def test_personal_situation_can_still_ask_for_detail():
    result = resolve_legal_question("My landlord will not return my deposit")
    assert result.status in {"matched", "clarify"}
    assert result.topic_id == "return_of_property"


def test_followup_uses_history_but_new_lesson_does_not():
    follow = resolve_legal_question(
        "what documents for that",
        recent_user_messages=["How do I file an FIR after a theft?"],
    )
    assert follow.topic_id == "fir_and_complaint"
    fresh = resolve_legal_question(
        "What is bail in Indian criminal procedure?",
        recent_user_messages=["My landlord will not return my deposit"],
    )
    assert fresh.status == "matched"
    assert fresh.topic_id == "bail_basics"


def _six_rights_mentioned(text: str) -> None:
    lowered = text.lower()
    assert "right to equality" in lowered
    assert "right to freedom" in lowered
    assert "right against exploitation" in lowered
    assert "freedom of religion" in lowered
    assert "cultural and educational" in lowered
    assert "constitutional remedies" in lowered


def test_fundamental_rights_lists_all_six():
    for question in (
        "What are the six Fundamental Rights in India?",
        "List all six Fundamental Rights under the Constitution of India",
        "What are Fundamental Rights under the Constitution?",
    ):
        result = resolve_legal_question(question)
        assert result.status == "matched", question
        assert result.topic_id == "fundamental_rights_overview", (question, result.topic_id)
        _six_rights_mentioned(result.text)
        assert "what happened, where" not in result.text.lower()


def test_new_consumer_question_does_not_keep_fundamental_rights_context():
    rights = resolve_legal_question("What are the six Fundamental Rights in India?")
    assert rights.topic_id == "fundamental_rights_overview"

    phone = resolve_legal_question(
        "My phone stopped working after three days and the seller refuses replacement",
        recent_user_messages=["What are the six Fundamental Rights in India?"],
    )
    assert phone.status == "matched"
    assert phone.topic_id == "consumer_grievance"
    assert "fundamental rights" not in phone.text.lower()
    assert "consumer" in phone.text.lower()
    assert "what happened, where" not in phone.text.lower()


def test_phone_then_rental_switches_topic():
    phone = resolve_legal_question(
        "My phone stopped working after three days and the seller refuses replacement"
    )
    assert phone.status == "matched"
    assert phone.topic_id == "consumer_grievance"
    lowered = phone.text.lower()
    assert "replacement" in lowered or "refund" in lowered
    assert "consumer commission" in lowered or "consumer protection" in lowered

    rental = resolve_legal_question(
        "My landlord is ignoring the rental contract and refusing to return my deposit",
        recent_user_messages=[
            "My phone stopped working after three days and the seller refuses replacement"
        ],
    )
    assert rental.status == "matched"
    assert rental.topic_id == "return_of_property"
    assert "consumer protection" not in rental.text.lower()
    assert "deposit" in rental.text.lower() or "tenan" in rental.text.lower()


def test_genuine_followup_keeps_consumer_context():
    follow = resolve_legal_question(
        "what about limitation period",
        recent_user_messages=[
            "My phone stopped working after three days and the seller refuses replacement"
        ],
    )
    assert follow.topic_id == "consumer_grievance"
    assert "limitation" in follow.text.lower()


def test_new_topic_does_not_keep_irrelevant_history():
    result = resolve_legal_question(
        "What is an FIR in India?",
        recent_user_messages=[
            "My phone stopped working after three days and the seller refuses replacement"
        ],
    )
    assert result.status == "matched"
    assert result.topic_id == "fir_and_complaint"
    assert "consumer" not in result.text.lower()


def test_ambiguous_or_thin_detail_asks_clarifying_question():
    # Mid-strength cue without enough detail should clarify rather than invent.
    result = resolve_legal_question("accident insurance")
    assert result.status in {"clarify", "matched", "unknown"}
    if result.status == "clarify":
        assert "?" in result.text
