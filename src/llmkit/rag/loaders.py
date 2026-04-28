"""Native markdown document loading helpers."""

from pathlib import Path

from llmkit.schemas.rag_outputs import RAGDocument


def load_markdown_documents(base_path: str | Path) -> list[RAGDocument]:
    """Load markdown documents recursively from a knowledge-base directory."""
    root = Path(base_path)
    if not root.exists():
        raise FileNotFoundError(f"Knowledge base path does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"Knowledge base path is not a directory: {root}")

    documents: list[RAGDocument] = []
    for file_path in sorted(root.rglob("*.md")):
        relative_path = file_path.relative_to(root)
        doc_type = relative_path.parts[0] if relative_path.parts else "root"
        text = file_path.read_text(encoding="utf-8").strip()
        documents.append(
            RAGDocument(
                text=text,
                metadata={
                    "source": file_path.as_posix(),
                    "file_name": file_path.name,
                    "doc_type": doc_type,
                },
            )
        )
    return documents
