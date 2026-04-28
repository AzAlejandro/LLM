# LLM Toolkit Release 01

Minimal Python toolkit for calling LLMs, reusing prompts, and validating structured outputs.

This release intentionally avoids RAG, memory, LangGraph, agents, tools, tracing, and deployment. It only includes the core pieces needed to run simple notebooks without duplicating setup code.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pip install -e .
```

Copy `.env.example` to `.env` and fill only the providers you want to test.

## Smoke Example

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

## Structured Output

Release 01 supports two structured-output paths.

Use native structured output with OpenAI models when you want the provider to
enforce a Pydantic schema during generation:

```python
from pydantic import BaseModel


class ClassificationOutput(BaseModel):
    category: str
    confidence: float
    rationale: str


response = llm.invoke_structured(
    system="Classify the request.",
    user="Explain REST APIs.",
    schema=ClassificationOutput,
)

print(response.parsed.category)
```

Use local parsing when you already have JSON text or when a provider does not
support native structured outputs:

1. The model is prompted to return JSON text.
2. The toolkit parses that text with `parse_json_output(raw_text, Schema)`.

That second path enforces the schema locally after generation, not by the
provider during generation. It is useful for teaching and debugging, but weaker
than native structured output because the model can still return valid JSON with
the wrong shape.

Use this path today when you want a lightweight example:

```python
from llmkit.schemas import ClassificationOutput, parse_json_output

response = llm.invoke(
    system="Return valid JSON only.",
    user='Classify this request into rag, agent, code, or general: "Explain REST APIs".',
)

parsed = parse_json_output(response.content, ClassificationOutput)
print(parsed)
```

Important distinction:

- Valid JSON: the text can be parsed.
- Schema-valid JSON: the parsed object also matches the Pydantic model.

## Tests

```powershell
.venv\Scripts\python -m pytest
```
