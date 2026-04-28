"""Transparent chat message helpers.

The notebooks show OpenAI-style chat messages explicitly before introducing the
toolkit helpers. ``build_messages`` is the tiny bridge between both views: it
takes the same ``system`` and ``user`` strings that ``LLMClient.invoke`` accepts
and returns the list of chat messages that provider SDKs expect.
"""


def build_messages(system: str, user: str) -> list[dict[str, str]]:
    """Build the chat message list sent to an LLM provider.

    Args:
        system: System instruction that defines role, behavior, tone, and output
            constraints.
        user: User message containing the concrete task and runtime inputs.

    Returns:
        A two-message chat list in the same shape used by OpenAI chat
        completions and many compatible providers.
    """
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
