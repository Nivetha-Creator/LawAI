
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import database
from app.services.ai_service import generate_text

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

    if request.conversation_id:
        conversation = database.get_conversation(request.conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")

        database.update_conversation(
            conversation["id"],
            mode="debate",
            side=side,
        )

    if not conversation:
        title_topic = (request.topic or request.message or "Legal debate").strip()
        conversation = database.create_conversation(
            title=f"Debate: {' '.join(title_topic.split())[:45]}",
            mode="debate",
            side=side,
        )

    if request.end_debate:
        transcript = database.get_conversation(
            conversation["id"]
        )["messages"]

        formatted = "\n".join(
            f'{item["role"].upper()}: {item["content"]}'
            for item in transcript[-30:]
        )

        review = generate_text(
            "You are a constructive debate coach. Review the educational debate "
            "transcript below. Score reasoning, evidence, rebuttals, clarity, and "
            "responsiveness from 1-10. Explain strengths, improvements, and give "
            "one practice exercise. Be balanced and do not predict a real court "
            "outcome. If there is not enough material, say so.\n\n"
            f"TRANSCRIPT:\n{formatted}"
        )

        database.add_message(
            conversation["id"],
            "assistant",
            "DEBATE REVIEW\n\n" + review,
        )

        return {
            "reply": review,
            "conversation_id": conversation["id"],
            "ended": True,
            "title": conversation["title"],
        }

    message = request.message.strip()

    if not message:
        message = f"Start a debate on this topic: {request.topic.strip()}"

    if not message.strip():
        raise HTTPException(
            status_code=400,
            detail="Enter a debate topic or argument.",
        )

    database.add_message(conversation["id"], "user", message)

    transcript = database.get_conversation(
        conversation["id"]
    )["messages"][-12:]

    history = "\n".join(
        f'{item["role"].upper()}: {item["content"]}'
        for item in transcript
    )

    opposing_side = "Defence" if side == "Prosecution" else "Prosecution"

    prompt = f"""
You are LawyerAI's educational debate partner.
The user represents {side}; you argue the opposing {opposing_side} side.
Challenge the user's reasoning respectfully, address their latest point,
and ask one focused follow-up question.

Do not invent legal sections, facts, precedents, or citations.
This is an educational exercise, not legal advice or a prediction of a real case.
Keep your response concise and clear.

DEBATE TRANSCRIPT:
{history}

Respond as the opposing side: {opposing_side}.
"""

    reply = generate_text(prompt)

    database.add_message(conversation["id"], "assistant", reply)

    return {
        "reply": reply,
        "conversation_id": conversation["id"],
        "ended": False,
        "title": conversation["title"],
    }
