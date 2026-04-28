"""Tests for the base RAG helpers."""

from pathlib import Path

from llmkit.llms.base import LLMResponse
from llmkit.memory import ChatMemoryStore
from llmkit.rag.answer import answer_with_context
from llmkit.rag.loaders import load_markdown_documents
from llmkit.rag.splitters import split_documents
from llmkit.rag.vectorstores import (
    build_chroma_index,
    open_chroma_index,
    read_index_metadata,
    retrieve_chunks,
)


def test_load_markdown_documents_reads_metadata(tmp_path: Path) -> None:
    """Markdown documents should load with source, file_name, and doc_type metadata."""
    kb = tmp_path / "knowledge_base"
    company = kb / "company"
    company.mkdir(parents=True)
    file_path = company / "overview.md"
    file_path.write_text("Insurellm overview.", encoding="utf-8")

    documents = load_markdown_documents(kb)

    assert len(documents) == 1
    assert documents[0].text == "Insurellm overview."
    assert documents[0].metadata["file_name"] == "overview.md"
    assert documents[0].metadata["doc_type"] == "company"
    assert documents[0].metadata["source"].endswith("overview.md")


def test_split_documents_creates_chunks_with_overlap_metadata(tmp_path: Path) -> None:
    """Chunking should preserve source metadata and add chunk metadata."""
    kb = tmp_path / "knowledge_base"
    process = kb / "process"
    process.mkdir(parents=True)
    text = ("sensor drift and cutting risk " * 40).strip()
    (process / "risk.md").write_text(text, encoding="utf-8")

    documents = load_markdown_documents(kb)
    chunks = split_documents(documents, chunk_size=120, chunk_overlap=20)

    assert len(chunks) > 1
    assert chunks[0].metadata["doc_type"] == "process"
    assert chunks[0].metadata["chunk_index"] == 0
    assert chunks[0].metadata["chunk_size"] == 120
    assert chunks[0].metadata["chunk_overlap"] == 20
    assert chunks[1].page_content


def test_chroma_index_builds_reopens_and_retrieves(monkeypatch, tmp_path: Path) -> None:
    """The vectorstore helper should persist chunks and retrieve top-k results."""
    kb = tmp_path / "knowledge_base"
    process = kb / "process"
    process.mkdir(parents=True)
    (process / "risk.md").write_text(
        "Cutting risk depends on speed, load, vibration, and moisture.",
        encoding="utf-8",
    )
    (process / "maintenance.md").write_text(
        "Maintenance plans track vibration, temperature, and bearing wear.",
        encoding="utf-8",
    )

    def fake_embed_texts(texts, model=None, client=None):
        vectors = []
        for text in texts:
            lower = text.lower()
            vectors.append(
                [
                    1.0 if "cutting" in lower else 0.0,
                    1.0 if "vibration" in lower else 0.0,
                    float(len(text)) / 100.0,
                ]
            )
        return vectors

    monkeypatch.setattr("llmkit.rag.vectorstores.embed_texts", fake_embed_texts)

    documents = load_markdown_documents(kb)
    chunks = split_documents(documents, chunk_size=200, chunk_overlap=20)
    persist_directory = tmp_path / "vectorstores" / "local_docs"

    collection = build_chroma_index(
        chunks,
        persist_directory=persist_directory,
        source_path=kb.as_posix(),
    )
    reopened = open_chroma_index(persist_directory)
    retrieved = retrieve_chunks(
        "What variables matter for cutting risk?",
        persist_directory=persist_directory,
        k=2,
    )
    metadata = read_index_metadata(persist_directory)

    assert collection.count() == len(chunks)
    assert reopened.count() == len(chunks)
    assert len(retrieved) == 2
    assert retrieved[0].metadata["source"].endswith(".md")
    assert metadata["source_path"] == kb.as_posix()
    assert metadata["chunk_size"] == 200
    assert metadata["chunk_overlap"] == 20
    assert metadata["embedding_model"] == "text-embedding-3-large"


def test_answer_with_context_builds_prompt_and_returns_rag_answer(monkeypatch, tmp_path: Path) -> None:
    """Answer helper should format sources, optional memory, and normalized output."""
    store = ChatMemoryStore(tmp_path / "chat.sqlite3")
    conversation = store.create_conversation("RAG memory")
    store.add_message(conversation.id, "user", "We are discussing cutting risk.")
    history = store.get_recent_messages(conversation.id, turns=1)

    class FakeLLM:
        def invoke(self, system: str, user: str, **kwargs) -> LLMResponse:
            return LLMResponse(
                content="Speed, vibration, and moisture are relevant variables.",
                model="fake-model",
                provider="openai",
                latency_seconds=0.01,
                usage=None,
                raw={"system": system, "user": user},
            )

    monkeypatch.setattr("llmkit.rag.answer.LLMFactory.create", lambda model_id=None: FakeLLM())

    result = answer_with_context(
        "Which variables are relevant?",
        retrieved_chunks=[
            {
                "page_content": "Cutting risk depends on speed, vibration, and moisture.",
                "metadata": {"source": "data/knowledge_base/process/risk.md"},
                "score": 0.95,
            }
        ],
        history=history,
    )

    assert result.answer.startswith("Speed, vibration")
    assert result.sources == ["data/knowledge_base/process/risk.md"]
    assert "Context:" in result.system_prompt
    assert "Recent conversation:" in result.user_prompt
    assert "Current user message: Which variables are relevant?" in result.user_prompt
