# LLM Toolkit

Local Python toolkit for learning and implementing LLM workflows step by step.

The repository currently includes:

- Release 01 foundations: provider-backed LLM clients, prompt reuse, and structured outputs.
- Release 02 base: native RAG helpers, persistent Chroma indexing, and memory reuse with SQLite.
- Teaching notebooks that show the manual flow first and only then the reusable helpers.

## Current Scope

The codebase is intentionally incremental. It is not trying to be a full framework yet.

- `src/llmkit/llms`: provider-backed clients created through `LLMFactory`
- `src/llmkit/prompts`: prompt templates and registry
- `src/llmkit/schemas`: Pydantic output models and parsing helpers
- `src/llmkit/memory`: SQLite-backed conversational memory
- `src/llmkit/rag`: document loading, chunking, embeddings, Chroma persistence, retrieval, and answering
- `notebooks/`: pedagogical walkthroughs from basic LLM calls to base RAG flows

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pip install -e .
```

Create `.env` from `.env.example` and fill only the providers you want to use.

## Environment

Minimal `.env` for the default path:

```env
OPENAI_API_KEY=your_key_here
LLMKIT_DEFAULT_PROVIDER=openai
LLMKIT_DEFAULT_MODEL=gpt-5.4-nano
LLMKIT_OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

Useful local paths:

- `data/knowledge_base/`: base RAG corpus
- `data/vectorstores/`: persistent Chroma indexes

The default knowledge base mirrors Ed Donner's `week5` Insurellm corpus:

- `company`
- `contracts`
- `employees`
- `products`

## Quick Smoke Example

```python
from llmkit.llms import LLMFactory
from llmkit.prompts import PromptRegistry

llm = LLMFactory.create("openai:gpt-5.4-nano")
prompt = PromptRegistry.get("chat.basic")

response = llm.invoke(
    system=prompt.system,
    user=prompt.render_user(topic="virtual sensors in paper processes"),
)

print(response.content)
```

## Structured Output Example

```python
from pydantic import BaseModel


class ClassificationOutput(BaseModel):
    category: str
    confidence: float
    rationale: str


llm = LLMFactory.create("openai:gpt-5.4-nano")
response = llm.invoke_structured(
    system="Classify the request.",
    user="Explain REST APIs.",
    schema=ClassificationOutput,
)

print(response.parsed.category)
```

## Base RAG Example

```python
from llmkit.rag import (
    answer_with_context,
    build_chroma_index,
    load_markdown_documents,
    retrieve_chunks,
    split_documents,
)

documents = load_markdown_documents("data/knowledge_base")
chunks = split_documents(documents, chunk_size=500, chunk_overlap=100)
build_chroma_index(
    chunks=chunks,
    index_name="insurellm",
    source_path="data/knowledge_base",
    chunk_size=500,
    chunk_overlap=100,
)

retrieved = retrieve_chunks("Who founded Insurellm?", index_name="insurellm", top_k=5)
answer = answer_with_context("Who founded Insurellm?", retrieved)

print(answer.answer)
for source in answer.sources:
    print(source)
```

## Notebooks

Current notebook sequence:

1. `01_llm_client_smoke_test.ipynb`
2. `02_business_brochure_generator.ipynb`
3. `03_deep_research_agentic_workflow.ipynb`
4. `04_pydantic_basemodel_structured_output.ipynb`
5. `05_async_llm_limits_basemodel.ipynb`
6. `06_gradio_chat_memory.ipynb`
7. `07_document_ingestion.ipynb`
8. `08_basic_rag.ipynb`
9. `09_rag_debugging.ipynb`
10. `10_rag_with_memory.ipynb`

## Tests

```powershell
.venv\Scripts\python -m pytest
```
