"""Tests for SQLite-backed chat memory."""

import sqlite3

import pytest

from llmkit.memory import ChatMemoryStore
from llmkit.memory.context import render_memory_prompt


def test_memory_store_creates_tables(tmp_path) -> None:
    """Opening the store should initialize the SQLite schema."""
    db_path = tmp_path / "chat.sqlite3"
    ChatMemoryStore(db_path)

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {"conversations", "messages"}.issubset(tables)


def test_memory_store_creates_conversation_and_lists_newest_first(tmp_path) -> None:
    """Conversations should persist and list with most recent first."""
    store = ChatMemoryStore(tmp_path / "chat.sqlite3")

    first = store.create_conversation("First")
    second = store.create_conversation("Second")

    conversations = store.list_conversations()

    assert conversations[0].id == second.id
    assert conversations[1].id == first.id
    assert conversations[0].title == "Second"


def test_memory_store_saves_and_reads_messages(tmp_path) -> None:
    """Messages should be stored by role and returned in chronological order."""
    store = ChatMemoryStore(tmp_path / "chat.sqlite3")
    conversation = store.create_conversation("Support")

    store.add_message(conversation.id, "user", "Hello")
    store.add_message(conversation.id, "assistant", "Hi")

    messages = store.get_messages(conversation.id)

    assert [message.role for message in messages] == ["user", "assistant"]
    assert [message.content for message in messages] == ["Hello", "Hi"]


def test_memory_store_returns_recent_turns(tmp_path) -> None:
    """Recent memory should keep only the requested number of user/assistant turns."""
    store = ChatMemoryStore(tmp_path / "chat.sqlite3")
    conversation = store.create_conversation("Window")
    for index in range(1, 5):
        store.add_message(conversation.id, "user", f"u{index}")
        store.add_message(conversation.id, "assistant", f"a{index}")

    messages = store.get_recent_messages(conversation.id, turns=2)

    assert [message.content for message in messages] == ["u3", "a3", "u4", "a4"]


def test_memory_store_clears_conversation(tmp_path) -> None:
    """Clearing should delete messages without deleting conversation metadata."""
    store = ChatMemoryStore(tmp_path / "chat.sqlite3")
    conversation = store.create_conversation("Clear me")
    store.add_message(conversation.id, "user", "Keep the chat id")

    store.clear_conversation(conversation.id)

    assert store.get_conversation(conversation.id).title == "Clear me"
    assert store.get_messages(conversation.id) == []


def test_memory_store_rejects_invalid_role(tmp_path) -> None:
    """Only user and assistant roles should be persisted."""
    store = ChatMemoryStore(tmp_path / "chat.sqlite3")
    conversation = store.create_conversation("Roles")

    with pytest.raises(ValueError, match="role"):
        store.add_message(conversation.id, "system", "nope")  # type: ignore[arg-type]


def test_render_memory_prompt_includes_history_and_current_message(tmp_path) -> None:
    """The chat prompt should render recent memory before the current message."""
    store = ChatMemoryStore(tmp_path / "chat.sqlite3")
    conversation = store.create_conversation("Context")
    store.add_message(conversation.id, "user", "My name is Alejo")
    store.add_message(conversation.id, "assistant", "I will remember that.")

    prompt = render_memory_prompt(
        "What is my name?",
        store.get_recent_messages(conversation.id, turns=1),
    )

    assert "Recent conversation:" in prompt
    assert "User: My name is Alejo" in prompt
    assert "Assistant: I will remember that." in prompt
    assert "Current user message: What is my name?" in prompt
