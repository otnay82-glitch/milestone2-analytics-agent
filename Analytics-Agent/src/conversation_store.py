import os
import sqlite3
import uuid
from datetime import datetime, timezone


DEFAULT_SQLITE_PATH = "./data/conversations.sqlite3"


def get_db_path() -> str:
    return os.getenv("SQLITE_PATH", DEFAULT_SQLITE_PATH)


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()

    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_user
                ON conversations(user_id);

            CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id);
            """
        )


def create_conversation(user_id: str) -> dict:
    conversation_id = str(uuid.uuid4())
    now = utc_now()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO conversations (
                id, user_id, title, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, user_id, "Percakapan baru", now, now),
        )

    return {
        "id": conversation_id,
        "title": "Percakapan baru",
        "updated_at": now,
    }


def list_conversations(user_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, updated_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_conversation(
    conversation_id: str,
    user_id: str,
) -> dict | None:
    with get_connection() as conn:
        conversation = conn.execute(
            """
            SELECT id, title, updated_at
            FROM conversations
            WHERE id = ?
              AND user_id = ?
            """,
            (conversation_id, user_id),
        ).fetchone()

        if conversation is None:
            return None

        messages = conn.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        ).fetchall()

    result = dict(conversation)
    result["messages"] = [dict(row) for row in messages]

    return result


def add_message(
    conversation_id: str,
    user_id: str,
    role: str,
    content: str,
) -> bool:
    message_id = str(uuid.uuid4())
    now = utc_now()

    with get_connection() as conn:
        owned = conn.execute(
            """
            SELECT 1
            FROM conversations
            WHERE id = ?
              AND user_id = ?
            """,
            (conversation_id, user_id),
        ).fetchone()

        if owned is None:
            return False

        conn.execute(
            """
            INSERT INTO messages (
                id, conversation_id, role, content, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, conversation_id, role, content, now),
        )

        conn.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
              AND user_id = ?
            """,
            (now, conversation_id, user_id),
        )

    return True

def get_messages(
    conversation_id: str,
    user_id: str,
    limit: int = 20,
) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = ?
              AND conversation_id IN (
                  SELECT id
                  FROM conversations
                  WHERE id = ?
                    AND user_id = ?
              )
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (conversation_id, conversation_id, user_id, limit),
        ).fetchall()

    messages = [dict(row) for row in rows]
    messages.reverse()
    return messages