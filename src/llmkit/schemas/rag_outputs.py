"""Small RAG data models for Release 02."""

from typing import Any

from pydantic import BaseModel, Field


class RAGDocument(BaseModel):
    """One loaded source document with metadata."""

    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGChunk(BaseModel):
    """One chunk derived from a source document."""

    page_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    """One retrieved chunk returned from the vectorstore."""

    page_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None


class RAGAnswer(BaseModel):
    """Normalized answer returned by the base RAG helper."""

    answer: str
    sources: list[str] = Field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    model: str
    provider: str
    system_prompt: str
    user_prompt: str
    context: str
