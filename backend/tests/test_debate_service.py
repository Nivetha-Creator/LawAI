from app.services.debate_service import generate_debate_feedback, generate_debate_reply


def _question_count(reply: str) -> int:
    follow = reply.split("**Follow-up:**", 1)
    body = follow[0]
    return body.count("?")


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


def test_debate_three_turns_counter_not_questions_then_evaluation():
    topic = "Abolition of the death penalty"
    user_side = "Prosecution"
    turns = [
        "Death penalty should be abolished because it is irreversible and the state should not kill.",
        "Also, poorer accused get worse counsel so the penalty is applied unequally.",
        "Deterrence is unproven, so a life sentence is the better policy.",
    ]
    transcript: list[dict[str, str]] = []
    replies: list[str] = []
    for message in turns:
        transcript.append({"role": "user", "content": message})
        reply = generate_debate_reply(user_side, topic, message, transcript)
        transcript.append({"role": "assistant", "content": reply})
        replies.append(reply)
        assert "Defence" in reply
        assert _question_count(reply) == 0
        assert "**Follow-up:**" in reply
        assert "still needs stronger support on facts and reasoning before a court" not in reply
        # Counter must engage the latest user point, not only quote it.
        latest = message.lower()
        combined = reply.lower()
        if "irreversible" in latest:
            assert "irreversib" in combined or "appeal" in combined or "clemency" in combined
        if "unequal" in latest or "poor" in latest:
            assert "uneven" in combined or "legal aid" in combined or "inequality" in combined
        if "deterrence" in latest:
            assert "deterr" in combined

    assert len(set(replies)) == 3

    feedback = generate_debate_feedback(transcript, user_side, topic)
    assert "Scores" in feedback
    assert "rule-based" in feedback.lower()
    assert "not an advanced AI assessment" in feedback
