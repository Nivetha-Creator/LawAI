from app import database


def test_conversation_crud_and_messages(temp_db):
    conv = database.create_conversation(title="Test chat", mode="chat")
    assert conv["id"]
    assert conv["title"] == "Test chat"

    database.add_message(conv["id"], "user", "Hello")
    database.add_message(conv["id"], "assistant", "Hi")

    loaded = database.get_conversation(conv["id"])
    assert len(loaded["messages"]) == 2

    listed = database.list_conversations()
    assert any(item["id"] == conv["id"] for item in listed)
    assert listed[0]["last_message"] == "Hi"

    updated = database.update_conversation(conv["id"], title="Renamed")
    assert updated["title"] == "Renamed"

    assert database.delete_conversation(conv["id"])
    assert database.get_conversation(conv["id"]) is None


def test_debate_topic_and_ended_persist(temp_db):
    conv = database.create_conversation(
        title="Debate",
        mode="debate",
        side="Prosecution",
        topic="Bail hearing",
    )
    database.update_conversation(conv["id"], ended=1)
    loaded = database.get_conversation(conv["id"])
    assert loaded["topic"] == "Bail hearing"
    assert loaded["ended"] == 1
