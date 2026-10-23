
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import database
from app.services.response_provider import generate_strategy_reply

router = APIRouter()


class StrategyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    conversation_id: int | None = None


@router.post("/strategy")
def strategy(request: StrategyRequest):
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Describe the legal situation you want analysed.",
        )

    conversation = None

    if request.conversation_id:
        conversation = database.get_conversation(request.conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")

        database.update_conversation(
            conversation["id"],
            mode="strategy",
            ended=0,
        )

    if not conversation:
        title = "Strategy: " + " ".join(message.split())[:48]
        conversation = database.create_conversation(
            title=title or "Legal strategy",
            mode="strategy",
        )

    database.add_message(conversation["id"], "user", message)

    transcript = database.get_conversation(conversation["id"])["messages"]

    reply, engine = generate_strategy_reply(message, transcript)

    database.add_message(conversation["id"], "assistant", reply)

    return {
        "reply": reply,
        "conversation_id": conversation["id"],
        "title": conversation["title"],
        "engine": engine,
        "mode": "strategy",
    }
