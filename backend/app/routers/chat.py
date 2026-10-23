
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import database
from app.services.response_provider import generate_chat_reply

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    conversation_id: int | None = None


@router.post("/chat")
def chat(request: ChatRequest):
    message = request.message.strip()

    if not message:
        raise HTTPException(status_code=400, detail="Enter a legal question.")

    conversation = None

    if request.conversation_id:
        conversation = database.get_conversation(request.conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")

        database.update_conversation(conversation["id"], mode="chat", ended=0)

    if not conversation:
        title = " ".join(message.split())[:55]
        conversation = database.create_conversation(
            title=title or "Legal question",
            mode="chat",
        )

    database.add_message(conversation["id"], "user", message)

    transcript = database.get_conversation(conversation["id"])["messages"]

    reply = generate_chat_reply(message, transcript)

    database.add_message(conversation["id"], "assistant", reply)

    return {
        "reply": reply,
        "conversation_id": conversation["id"],
        "title": conversation["title"],
        "engine": "local",
    }
