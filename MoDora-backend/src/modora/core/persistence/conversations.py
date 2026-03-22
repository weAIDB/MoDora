from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import secrets

from modora.core.persistence.db import connect_db
from modora.core.settings import Settings


@dataclass(frozen=True)
class ConversationRecord:
    id: str
    user_id: str
    title: str
    created_at: str


@dataclass(frozen=True)
class ConversationMessageRecord:
    id: str
    role: str
    content: str
    citations: list[dict]
    sort_index: int
    created_at: str


def generate_conversation_id() -> str:
    return f"conv_{secrets.token_urlsafe(12)}"


def generate_message_id() -> str:
    return f"msg_{secrets.token_urlsafe(12)}"


def create_conversation(
    settings: Settings,
    *,
    user_id: str,
    title: str,
) -> ConversationRecord:
    conversation_id = generate_conversation_id()
    created_at = datetime.now(timezone.utc).isoformat()
    with connect_db(settings) as conn:
        conn.execute(
            """
            INSERT INTO conversations (id, user_id, title, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, user_id, title, created_at),
        )
    return ConversationRecord(
        id=conversation_id,
        user_id=user_id,
        title=title,
        created_at=created_at,
    )


def update_conversation(
    settings: Settings,
    *,
    user_id: str,
    conversation_id: str,
    title: str,
    document_ids: list[str],
    messages: list[dict],
) -> None:
    with connect_db(settings) as conn:
        owner = conn.execute(
            "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
        if owner is None:
            raise ValueError("conversation not found")

        conn.execute(
            "UPDATE conversations SET title = ? WHERE id = ? AND user_id = ?",
            (title, conversation_id, user_id),
        )
        conn.execute(
            "DELETE FROM conversation_documents WHERE conversation_id = ?",
            (conversation_id,),
        )
        for document_id in document_ids:
            if not document_id:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO conversation_documents (conversation_id, document_id)
                VALUES (?, ?)
                """,
                (conversation_id, document_id),
            )

        conn.execute(
            "DELETE FROM conversation_messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        for idx, message in enumerate(messages):
            conn.execute(
                """
                INSERT INTO conversation_messages (
                    id, conversation_id, role, content, citations_json, sort_index, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generate_message_id(),
                    conversation_id,
                    message.get("role", "assistant"),
                    message.get("content", ""),
                    json.dumps(message.get("citations", []), ensure_ascii=False),
                    idx,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )


def delete_conversation(
    settings: Settings,
    *,
    user_id: str,
    conversation_id: str,
) -> None:
    with connect_db(settings) as conn:
        conn.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        )


def list_conversations_for_user(
    settings: Settings,
    *,
    user_id: str,
) -> list[dict]:
    with connect_db(settings) as conn:
        conversations = conn.execute(
            """
            SELECT id, user_id, title, created_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()

        rows = []
        for conversation in conversations:
            document_rows = conn.execute(
                """
                SELECT d.id, d.original_name, d.storage_key, d.status, d.created_at
                FROM conversation_documents cd
                JOIN documents d ON d.id = cd.document_id
                WHERE cd.conversation_id = ?
                ORDER BY d.created_at ASC
                """,
                (conversation["id"],),
            ).fetchall()
            message_rows = conn.execute(
                """
                SELECT role, content, citations_json, sort_index, created_at
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY sort_index ASC
                """,
                (conversation["id"],),
            ).fetchall()
            rows.append(
                {
                    "id": conversation["id"],
                    "title": conversation["title"],
                    "created_at": conversation["created_at"],
                    "documents": [
                        {
                            "id": row["id"],
                            "original_name": row["original_name"],
                            "storage_key": row["storage_key"],
                            "status": row["status"],
                            "created_at": row["created_at"],
                        }
                        for row in document_rows
                    ],
                    "messages": [
                        {
                            "role": row["role"],
                            "content": row["content"],
                            "citations": json.loads(row["citations_json"] or "[]"),
                            "sort_index": row["sort_index"],
                            "created_at": row["created_at"],
                        }
                        for row in message_rows
                    ],
                }
            )
    return rows
