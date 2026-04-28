"""Simple native chunking helpers for Release 02."""

from llmkit.schemas.rag_outputs import RAGChunk, RAGDocument


def _pick_boundary(text: str, start: int, end: int) -> int:
    """Prefer paragraph, line, or word boundaries near the end of a chunk."""
    if end >= len(text):
        return len(text)

    window = text[start:end]
    search_start = max(0, int(len(window) * 0.6))
    for separator in ("\n\n", "\n", " "):
        position = window.rfind(separator, search_start)
        if position > 0:
            return start + position + len(separator)
    return end


def split_documents(
    documents: list[RAGDocument],
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[RAGChunk]:
    """Split documents into chunks using simple character windows."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    chunks: list[RAGChunk] = []
    for document in documents:
        text = document.text.strip()
        if not text:
            continue

        start = 0
        chunk_index = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            boundary = _pick_boundary(text, start, end)
            chunk_text = text[start:boundary].strip()
            if chunk_text:
                metadata = dict(document.metadata)
                metadata.update(
                    {
                        "chunk_index": chunk_index,
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap,
                    }
                )
                chunks.append(RAGChunk(page_content=chunk_text, metadata=metadata))
                chunk_index += 1

            if boundary >= len(text):
                break
            start = max(boundary - chunk_overlap, start + 1)

    return chunks
