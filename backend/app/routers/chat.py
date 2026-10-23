
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import database
from app.services.ai_service import generate_text

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    conversation_id: int | None = None


SYSTEM_PROMPT = """
You are LawyerAI, an Indian legal information assistant, not a lawyer.

Explain general Indian legal information in clear, simple English.
Summarize the issue, identify potentially relevant laws only when confident,
explain practical next steps, and mention facts that could change the answer.

India's new criminal-law framework, including BNS, BNSS and BSA, took effect
on 1 July 2024, subject to transitional rules and the circumstances of the case.
Do not automatically apply the older IPC, CrPC or Evidence Act to every case.

Never invent legal sections, court judgments, citations, or official URLs.
If uncertain, clearly say so. Recommend checking official legislation at
https://www.indiacode.nic.in/ and consulting a qualified Indian advocate.

This is general information, not personalized legal advice. For immediate
danger, advise the person to contact local emergency services or police.
"""


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

        database.update_conversation(conversation["id"], mode="chat")

    if not conversation:
        title = " ".join(message.split())[:55]
        conversation = database.create_conversation(
            title=title or "Legal question",
            mode="chat",
        )

    database.add_message(conversation["id"], "user", message)

    recent_messages = database.get_conversation(
        conversation["id"]
    )["messages"][-12:]

    history = "\n".join(
        f'{item["role"].upper()}: {item["content"]}'
        for item in recent_messages
    )

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Conversation:\n{history}\n\n"
        "Answer the latest user message."
    )

    reply = generate_text(prompt)

    database.add_message(conversation["id"], "assistant", reply)

    return {
        "reply": reply,
        "conversation_id": conversation["id"],
        "title": conversation["title"],
    }
