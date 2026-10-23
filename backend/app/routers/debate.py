
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import database
from app.services.response_provider import generate_debate_review, generate_debate_turn

router = APIRouter()


class DebateRequest(BaseModel):
    message: str = ""
    side: str = "Defence"
    end_debate: bool = False
    conversation_id: int | None = None
    topic: str = ""


def normalize_side(side):
    value = side.strip().lower()

    if value == "prosecution":
        return "Prosecution"

    if value in {"defence", "defense"}:
        return "Defence"

    return None


@router.post("/debate")
def debate(request: DebateRequest):
    side = normalize_side(request.side)

    if not side:
        raise HTTPException(
            status_code=400,
            detail="Choose Prosecution or Defence.",
        )

    conversation = None
    topic = (request.topic or "").strip()

    if request.conversation_id:
        conversation = database.get_conversation(request.conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")

        if not topic:
            topic = (conversation.get("topic") or "").strip()

        database.update_conversation(
            conversation["id"],
            mode="debate",
            side=side,
            topic=topic or None,
        )

    if not conversation:
        title_topic = topic or request.message.strip() or "Legal debate"
        conversation = database.create_conversation(
            title=f"Debate: {' '.join(title_topic.split())[:45]}",
            mode="debate",
            side=side,
            topic=topic,
        )

    if request.end_debate:
        transcript = database.get_conversation(conversation["id"])["messages"]

        review = generate_debate_review(transcript, side, topic)

        review_body = "DEBATE REVIEW\n\n" + review

        database.add_message(conversation["id"], "assistant", review_body)
        database.update_conversation(conversation["id"], ended=1)

        return {
            "reply": review_body,
            "conversation_id": conversation["id"],
            "ended": True,
            "title": conversation["title"],
            "engine": "local",
        }

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Enter a debate topic or argument.",
        )

    if not topic:
        topic = (conversation.get("topic") or "").strip()
        if topic:
            database.update_conversation(conversation["id"], topic=topic)

    database.add_message(conversation["id"], "user", message)

    transcript = database.get_conversation(conversation["id"])["messages"]

    reply = generate_debate_turn(side, topic, message, transcript)

    database.add_message(conversation["id"], "assistant", reply)

    return {
        "reply": reply,
        "conversation_id": conversation["id"],
        "ended": False,
        "title": conversation["title"],
        "engine": "local",
    }
