"""Embedding helpers for the base RAG release."""

from collections.abc import Sequence

from openai import OpenAI

from llmkit.config.settings import get_settings


def build_openai_embedding_client() -> OpenAI:
    """Create an OpenAI client for embedding requests."""
    settings = get_settings()
    return OpenAI(api_key=settings.require_openai_api_key())


def resolve_embedding_model(model: str | None = None) -> str:
    """Return the configured OpenAI embedding model name."""
    return model or get_settings().openai_embedding_model


def embed_texts(
    texts: Sequence[str],
    model: str | None = None,
    client: OpenAI | None = None,
) -> list[list[float]]:
    """Embed a sequence of texts with the configured OpenAI embedding model."""
    if not texts:
        return []
    resolved_model = resolve_embedding_model(model)
    active_client = client or build_openai_embedding_client()
    response = active_client.embeddings.create(model=resolved_model, input=list(texts))
    return [item.embedding for item in response.data]
