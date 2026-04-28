"""Answering helper for the base RAG release."""

from collections.abc import Sequence
from typing import Any

from llmkit.llms import LLMFactory
from llmkit.memory import StoredMessage
from llmkit.memory.context import render_memory_prompt
from llmkit.schemas.rag_outputs import RAGAnswer, RetrievedChunk

DEFAULT_RAG_SYSTEM_PROMPT = (
    "You answer questions using the provided context when it is relevant. "
    "If the answer is not supported by the context, say so clearly.\n\n"
    "Context:\n{context}"
)


def build_rag_context(retrieved_chunks: Sequence[RetrievedChunk]) -> str:
    """Format retrieved chunks into a readable RAG context block."""
    sections: list[str] = []
    for index, chunk in enumerate(retrieved_chunks, start=1):
        source = chunk.metadata.get("source", "unknown source")
        header = f"[Chunk {index}] Source: {source}"
        if chunk.score is not None:
            header += f" | Score: {chunk.score:.4f}"
        sections.append(f"{header}\n{chunk.page_content}")
    return "\n\n".join(sections)


def _normalize_retrieved_chunks(
    retrieved_chunks: Sequence[RetrievedChunk | dict[str, Any]],
) -> list[RetrievedChunk]:
    """Accept model instances or plain dictionaries for notebook-friendly use."""
    return [
        chunk if isinstance(chunk, RetrievedChunk) else RetrievedChunk.model_validate(chunk)
        for chunk in retrieved_chunks
    ]


def answer_with_context(
    question: str,
    retrieved_chunks: Sequence[RetrievedChunk | dict[str, Any]],
    history: Sequence[StoredMessage] | None = None,
    model_id: str | None = None,
    system_prompt: str | None = None,
) -> RAGAnswer:
    """Answer a question using retrieved chunks and optional recent history."""
    normalized_chunks = _normalize_retrieved_chunks(retrieved_chunks)
    context = build_rag_context(normalized_chunks)
    final_system_prompt = (system_prompt or DEFAULT_RAG_SYSTEM_PROMPT).format(context=context)
    user_prompt = render_memory_prompt(question, list(history)) if history else question.strip()

    llm = LLMFactory.create(model_id)
    response = llm.invoke(system=final_system_prompt, user=user_prompt)

    sources = list(
        dict.fromkeys(chunk.metadata.get("source", "unknown source") for chunk in normalized_chunks)
    )
    return RAGAnswer(
        answer=response.content,
        sources=sources,
        retrieved_chunks=normalized_chunks,
        model=response.model,
        provider=response.provider,
        system_prompt=final_system_prompt,
        user_prompt=user_prompt,
        context=context,
    )
