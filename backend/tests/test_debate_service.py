from app.services.debate_service import generate_debate_feedback, generate_debate_reply


def test_debate_reply_addresses_user_message():
    transcript = [{"role": "user", "content": "CCTV alone cannot prove intent beyond doubt."}]
    reply = generate_debate_reply(
        "Defence",
        "CCTV as sole evidence",
        transcript[0]["content"],
        transcript,
    )
    assert "CCTV" in reply or "cctv" in reply.lower()
    assert "educational" in reply.lower()


def test_debate_feedback_scores_user_text():
    transcript = [
        {"role": "user", "content": "Because the footage is unclear, therefore intent is not proved. We need witness testimony."},
        {"role": "assistant", "content": "Opposing point"},
        {"role": "user", "content": "However, the prosecution must still prove guilt beyond reasonable doubt with evidence."},
    ]
    feedback = generate_debate_feedback(transcript, "Defence", "CCTV evidence")
    assert "rule-based" in feedback.lower()
    assert "Scores" in feedback
    assert "not an advanced AI assessment" in feedback


def test_debate_feedback_requires_user_messages():
    feedback = generate_debate_feedback([], "Prosecution", "Bail")
    assert "not enough" in feedback.lower()
