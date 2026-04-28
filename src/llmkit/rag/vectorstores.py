"""Small Chroma helpers for the base RAG release."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chromadb import PersistentClient

from llmkit.config.settings import get_settings
from llmkit.rag.embeddings import embed_texts, resolve_embedding_model
from llmkit.schemas.rag_outputs import RAGChunk, RetrievedChunk

DEFAULT_COLLECTION_NAME = "documents"
INDEX_METADATA_FILE = "index_metadata.json"


def _metadata_path(persist_directory: str | Path) -> Path:
    return Path(persist_directory) / INDEX_METADATA_FILE


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _normalize_persist_directory(persist_directory: str | Path | None) -> Path:
    if persist_directory is None:
        return get_settings().vectorstore_dir / "local_docs"
    return Path(persist_directory)


def _write_index_metadata(
    persist_directory: Path,
    *,
    embedding_model: str,
    source_path: str | None,
    chunk_size: int | None,
    chunk_overlap: int | None,
) -> None:
    persist_directory.mkdir(parents=True, exist_ok=True)
    metadata = {
        "embedding_model": embedding_model,
        "source_path": source_path,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "created_at": _now_iso(),
    }
    _metadata_path(persist_directory).write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


def read_index_metadata(persist_directory: str | Path) -> dict[str, Any]:
    """Read simple metadata written alongside the persistent Chroma index."""
    path = _metadata_path(persist_directory)
    if not path.exists():
        raise FileNotFoundError(f"Index metadata file does not exist: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def open_chroma_index(
    persist_directory: str | Path | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
):
    """Open or create the configured persistent Chroma collection."""
    directory = _normalize_persist_directory(persist_directory)
    client = PersistentClient(path=str(directory))
    return client.get_or_create_collection(collection_name)


def build_chroma_index(
    chunks: list[RAGChunk],
    persist_directory: str | Path | None = None,
    *,
    embedding_model: str | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    source_path: str | None = None,
    recreate: bool = True,
):
    """Build a persistent Chroma index from chunked documents."""
    directory = _normalize_persist_directory(persist_directory)
    directory.mkdir(parents=True, exist_ok=True)
    client = PersistentClient(path=str(directory))

    if recreate:
        existing = {collection.name for collection in client.list_collections()}
        if collection_name in existing:
            client.delete_collection(collection_name)

    collection = client.get_or_create_collection(collection_name)
    texts = [chunk.page_content for chunk in chunks]
    vectors = embed_texts(texts, model=embedding_model)
    ids = [
        f"{chunk.metadata.get('file_name', 'chunk')}-{chunk.metadata.get('chunk_index', index)}"
        for index, chunk in enumerate(chunks)
    ]
    metadatas = [chunk.metadata for chunk in chunks]

    if texts:
        collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)

    first_metadata = chunks[0].metadata if chunks else {}
    _write_index_metadata(
        directory,
        embedding_model=resolve_embedding_model(embedding_model),
        source_path=source_path,
        chunk_size=first_metadata.get("chunk_size"),
        chunk_overlap=first_metadata.get("chunk_overlap"),
    )
    return collection


def retrieve_chunks(
    question: str,
    persist_directory: str | Path | None = None,
    *,
    k: int = 4,
    embedding_model: str | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> list[RetrievedChunk]:
    """Retrieve top-k chunks for a question from a persistent Chroma index."""
    collection = open_chroma_index(persist_directory, collection_name=collection_name)
    query_vector = embed_texts([question], model=embedding_model)[0]
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    retrieved: list[RetrievedChunk] = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        score = None if distance is None else 1.0 / (1.0 + float(distance))
        retrieved.append(
            RetrievedChunk(
                page_content=document,
                metadata=metadata or {},
                score=score,
            )
        )
    return retrieved
