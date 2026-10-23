
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DATABASE_PATH", "lawyerai.db")

if not Path(DB_PATH).is_absolute():
    DB_PATH = str(Path(__file__).resolve().parents[1] / DB_PATH)


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT 'New conversation',
            mode TEXT NOT NULL DEFAULT 'chat',
            side TEXT NOT NULL DEFAULT 'Defence',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_messages_conversation
        ON messages(conversation_id, id);
        """)


def create_conversation(title="New conversation", mode="chat", side="Defence"):
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO conversations(title, mode, side) VALUES (?, ?, ?)",
            (title[:80] or "New conversation", mode, side),
        )
        conversation_id = cursor.lastrowid

    return get_conversation(conversation_id)


def get_conversation(conversation_id):
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()

        if not row:
            return None

        result = dict(row)
        result["messages"] = [
            dict(message)
            for message in conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id",
                (conversation_id,),
            ).fetchall()
        ]

        return result


def list_conversations():
    with connect() as conn:
        rows = conn.execute("""
            SELECT c.*,
                (SELECT content FROM messages m
                 WHERE m.conversation_id = c.id
                 ORDER BY m.id DESC LIMIT 1) AS last_message
            FROM conversations c
            ORDER BY c.updated_at DESC, c.id DESC
        """).fetchall()

        return [dict(row) for row in rows]


def add_message(conversation_id, role, content):
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages(conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )


def update_conversation(conversation_id, title=None, mode=None, side=None):
    updates = []
    values = []

    for field, value in (
        ("title", title),
        ("mode", mode),
        ("side", side),
    ):
        if value is not None:
            updates.append(f"{field} = ?")
            values.append(value)

    if not updates:
        return get_conversation(conversation_id)

    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(conversation_id)

    with connect() as conn:
        conn.execute(
            f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
            values,
        )

    return get_conversation(conversation_id)


def delete_conversation(conversation_id):
    with connect() as conn:
        cursor = conn.execute(
            "DELETE FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        return cursor.rowcount > 0
