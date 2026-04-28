"""Local Gradio chat app with SQLite-backed memory."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import gradio as gr
except ImportError as exc:  # pragma: no cover - user-facing runtime guard
    raise SystemExit(
        "Gradio is not installed. Run `.venv\\Scripts\\python -m pip install -r requirements.txt`."
    ) from exc

from llmkit.config.settings import get_settings
from llmkit.llms import LLMFactory
from llmkit.memory import ChatMemoryStore, Conversation, StoredMessage
from llmkit.memory.context import render_memory_prompt

DB_PATH = Path(os.getenv("LLMKIT_CHAT_MEMORY_DB", ROOT / "data" / "chat_memory.sqlite3"))
MEMORY_TURNS = int(os.getenv("LLMKIT_CHAT_MEMORY_TURNS", "8"))
SERVER_PORT = int(os.getenv("LLMKIT_GRADIO_PORT", "8009"))
SYSTEM_PROMPT = os.getenv(
    "LLMKIT_CHAT_SYSTEM_PROMPT",
    "You are a concise, practical assistant. Use the recent conversation only when it helps answer the current message.",
)

STORE = ChatMemoryStore(DB_PATH)


def _conversation_label(conversation: Conversation) -> str:
    return f"{conversation.id}: {conversation.title}"


def _conversation_id(label: str | None) -> int:
    if not label:
        return _ensure_conversation().id
    return int(label.split(":", 1)[0])


def _conversation_choices() -> list[str]:
    conversations = STORE.list_conversations()
    if not conversations:
        conversations = [STORE.create_conversation()]
    return [_conversation_label(item) for item in conversations]


def _ensure_conversation() -> Conversation:
    conversations = STORE.list_conversations()
    if conversations:
        return conversations[0]
    return STORE.create_conversation()


def _messages_for_chatbot(messages: list[StoredMessage]) -> list[dict[str, str]]:
    return [
        {"role": item.role, "content": item.content}
        for item in messages
        if item.role in {"user", "assistant"}
    ]


def _conversation_update(label: str) -> gr.Dropdown:
    return gr.update(choices=_conversation_choices(), value=label)


def _load_conversation(label: str | None):
    conversation_id = _conversation_id(label)
    messages = STORE.get_messages(conversation_id)
    choices = _conversation_choices()
    current_label = next(
        (choice for choice in choices if choice.startswith(f"{conversation_id}:")),
        choices[0],
    )
    return _messages_for_chatbot(messages), gr.update(choices=choices, value=current_label)


def create_conversation():
    conversation = STORE.create_conversation()
    return [], _conversation_update(_conversation_label(conversation))


def clear_conversation(label: str | None):
    conversation_id = _conversation_id(label)
    STORE.clear_conversation(conversation_id)
    return _load_conversation(label)


def respond(
    message: str,
    chat_history: list[dict[str, str]],
    conversation_label: str | None,
    model_id: str,
):
    clean_message = message.strip()
    if not clean_message:
        label = conversation_label or _conversation_choices()[0]
        return "", chat_history, _conversation_update(label)

    conversation_id = _conversation_id(conversation_label)
    recent_history = STORE.get_recent_messages(conversation_id, turns=MEMORY_TURNS)
    user_prompt = render_memory_prompt(clean_message, recent_history)

    STORE.add_message(conversation_id, "user", clean_message)
    updated_history = chat_history + [{"role": "user", "content": clean_message}]

    try:
        llm = LLMFactory.create(model_id.strip() or None)
        response = llm.invoke(system=SYSTEM_PROMPT, user=user_prompt)
        assistant_message = response.content.strip() or "(empty response)"
    except Exception as exc:  # pragma: no cover - Gradio runtime feedback
        assistant_message = f"Error: {exc}"
        label = conversation_label or _conversation_choices()[0]
        return "", updated_history + [{"role": "assistant", "content": assistant_message}], _conversation_update(label)

    STORE.add_message(conversation_id, "assistant", assistant_message)
    choices = _conversation_choices()
    current_label = next(
        (choice for choice in choices if choice.startswith(f"{conversation_id}:")),
        conversation_label or choices[0],
    )
    return "", updated_history + [{"role": "assistant", "content": assistant_message}], gr.update(choices=choices, value=current_label)


APP_CSS = """
.gradio-container { max-width: 1120px !important; margin: 0 auto !important; }
#chatbot { min-height: 520px; }
.llmkit-row { align-items: end; }
"""


def build_app() -> gr.Blocks:
    settings = get_settings()
    initial_conversation = _ensure_conversation()
    initial_label = _conversation_label(initial_conversation)
    initial_messages = _messages_for_chatbot(STORE.get_messages(initial_conversation.id))

    with gr.Blocks(title="LLMKit Chat") as demo:
        with gr.Row(elem_classes=["llmkit-row"]):
            model_id = gr.Textbox(
                label="Model",
                value=settings.default_model,
                scale=2,
            )
            conversation = gr.Dropdown(
                label="Conversation",
                choices=_conversation_choices(),
                value=initial_label,
                allow_custom_value=False,
                scale=3,
            )
            new_button = gr.Button("New", variant="secondary")
            clear_button = gr.Button("Clear", variant="secondary")

        chatbot = gr.Chatbot(
            value=initial_messages,
            elem_id="chatbot",
        )
        message = gr.Textbox(
            label="Message",
            placeholder="Type a message, then press Enter or Send",
            lines=3,
        )
        send_button = gr.Button("Send", variant="primary")

        message.submit(
            respond,
            inputs=[message, chatbot, conversation, model_id],
            outputs=[message, chatbot, conversation],
        )
        send_button.click(
            respond,
            inputs=[message, chatbot, conversation, model_id],
            outputs=[message, chatbot, conversation],
        )
        conversation.change(
            _load_conversation,
            inputs=[conversation],
            outputs=[chatbot, conversation],
        )
        new_button.click(
            create_conversation,
            outputs=[chatbot, conversation],
        )
        clear_button.click(
            clear_conversation,
            inputs=[conversation],
            outputs=[chatbot, conversation],
        )

    return demo


if __name__ == "__main__":
    build_app().launch(
        css=APP_CSS,
        server_name="127.0.0.1",
        server_port=SERVER_PORT,
    )
