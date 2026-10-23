
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import database

router = APIRouter(prefix="/conversations", tags=["Conversation history"])


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


@router.get("")
def list_conversations():
    return database.list_conversations()


@router.post("")
def create_conversation():
    return database.create_conversation()


@router.get("/{conversation_id}")
def get_conversation(conversation_id: int):
    item = database.get_conversation(conversation_id)

    if not item:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return item


@router.patch("/{conversation_id}")
def rename_conversation(conversation_id: int, request: RenameRequest):
    if not database.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return database.update_conversation(
        conversation_id,
        title=request.title.strip(),
    )


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: int):
    if not database.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return {"deleted": True}
