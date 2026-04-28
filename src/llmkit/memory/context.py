"""Prompt rendering helpers for chat memory."""

from llmkit.memory.sqlite_memory import StoredMessage


def render_memory_prompt(
    current_message: str,
    history: list[StoredMessage],
) -> str:
    """Render recent memory and the current message into one user prompt."""
    current = current_message.strip()
    if not history:
        return current

    lines = ["Recent conversation:"]
    for item in history:
        label = "User" if item.role == "user" else "Assistant"
        lines.append(f"{label}: {item.content}")
    lines.extend(["", f"Current user message: {current}"])
    return "\n".join(lines)
