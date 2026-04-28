"""Persistent SQLite memory for local chat applications."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class Conversation:
    """One persisted chat conversation."""

    id: int
    title: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class StoredMessage:
    """One persisted chat message."""

    id: int
    conversation_id: int
    role: Role
    content: str
    created_at: str


class ChatMemoryStore:
    """Small SQLite store for conversation-level chat memory."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id)
                        REFERENCES conversations(id)
                        ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
                ON messages(conversation_id, id)
                """
            )

    def create_conversation(self, title: str | None = None) -> Conversation:
        """Create a conversation and return its stored metadata."""
        timestamp = self._now()
        clean_title = (title or "New chat").strip() or "New chat"
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO conversations(title, created_at, updated_at)
                VALUES (?, ?, ?)
                """,
                (clean_title, timestamp, timestamp),
            )
            conversation_id = int(cursor.lastrowid)
        return self.get_conversation(conversation_id)

    def get_conversation(self, conversation_id: int) -> Conversation:
        """Return one conversation or raise ``KeyError`` if it does not exist."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Conversation {conversation_id} does not exist.")
        return Conversation(**dict(row))

    def list_conversations(self) -> list[Conversation]:
        """List conversations from newest to oldest."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
        return [Conversation(**dict(row)) for row in rows]

    def add_message(self, conversation_id: int, role: Role, content: str) -> StoredMessage:
        """Persist one user or assistant message."""
        if role not in ("user", "assistant"):
            raise ValueError("role must be 'user' or 'assistant'.")
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("content must not be empty.")

        timestamp = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages(conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, clean_content, timestamp),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (timestamp, conversation_id),
            )
            message_id = int(cursor.lastrowid)
        return self.get_message(message_id)

    def get_message(self, message_id: int) -> StoredMessage:
        """Return one stored message or raise ``KeyError`` if missing."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, conversation_id, role, content, created_at
                FROM messages
                WHERE id = ?
                """,
                (message_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Message {message_id} does not exist.")
        return StoredMessage(**dict(row))

    def get_messages(self, conversation_id: int) -> list[StoredMessage]:
        """Return all messages for a conversation in chronological order."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, conversation_id, role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,),
            ).fetchall()
        return [StoredMessage(**dict(row)) for row in rows]

    def get_recent_messages(self, conversation_id: int, turns: int = 8) -> list[StoredMessage]:
        """Return the last ``turns`` user/assistant pairs in chronological order."""
        if turns < 1:
            return []
        message_limit = turns * 2
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, conversation_id, role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, message_limit),
            ).fetchall()
        return [StoredMessage(**dict(row)) for row in reversed(rows)]

    def clear_conversation(self, conversation_id: int) -> None:
        """Delete all messages from a conversation while keeping its metadata."""
        timestamp = self._now()
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (timestamp, conversation_id),
            )

    def delete_conversation(self, conversation_id: int) -> None:
        """Delete a conversation and all its messages."""
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )

    def rename_conversation(self, conversation_id: int, title: str) -> None:
        """Update the title for a conversation."""
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("title must not be empty.")
        timestamp = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (clean_title, timestamp, conversation_id),
            )
