from app.services.legal_service import answer_legal_question, match_topics


def test_match_topics_bns():
    matches = match_topics("What is the difference between BNS and IPC?")
    assert matches
    assert matches[0][0]["id"] == "bns_ipc_transition"


def test_known_answer_includes_knowledge_marker():
    reply = answer_legal_question("Explain BNS BNSS BSA criminal law July 2024")
    assert "curated knowledge base" in reply
    assert "local legal information engine" in reply


def test_unknown_question_does_not_fabricate():
    reply = answer_legal_question(
        "What is the exact section number for a niche tax dispute in 1987?"
    )
    assert "do not have curated information" in reply.lower()
    assert "will not guess" in reply.lower()
