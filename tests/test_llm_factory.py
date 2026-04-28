"""Tests for LLM factory parsing and configuration errors."""

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from llmkit.llms.base import StructuredLLMError
from llmkit.llms.factory import LLMFactory
from llmkit.llms.messages import build_messages
from llmkit.llms.openai_client import OpenAIClient


class StructuredSmokeOutput(BaseModel):
    """Small schema used to test native structured-output calls."""

    answer: str
    score: float


class StructuredMetricOutput(BaseModel):
    """Closed metric schema compatible with OpenAI structured outputs."""

    name: str
    value: float
    target: float
    passed: bool


class StructuredExperimentOutput(BaseModel):
    """Experiment schema that avoids dynamic dict keys in structured output."""

    experiment_name: str
    overall_score: float
    summary_metrics: list[StructuredMetricOutput]


class FakeUsage:
    """Minimal usage payload with the SDK's ``model_dump`` shape."""

    def model_dump(self) -> dict[str, int]:
        return {"total_tokens": 7}


class FakeParsedMessage:
    """Minimal parsed chat message returned by the fake OpenAI SDK."""

    def __init__(
        self,
        parsed: StructuredSmokeOutput | None,
        content: str | None = None,
        refusal: str | None = None,
    ) -> None:
        self.parsed = parsed
        self.content = content
        self.refusal = refusal


class FakeParsedResponse:
    """Minimal parsed response returned by ``chat.completions.parse``."""

    def __init__(self, message: FakeParsedMessage) -> None:
        self.choices = [SimpleNamespace(message=message)]
        self.usage = FakeUsage()

    def model_dump(self) -> dict[str, str]:
        return {"id": "fake-response"}


class FakeParsedCompletions:
    """Capture parsed completion kwargs without calling the network."""

    def __init__(self, response: FakeParsedResponse) -> None:
        self.response = response
        self.kwargs: dict | None = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def test_parse_model_id_allows_colons_inside_model_name() -> None:
    """Ollama-style model names can contain additional colons."""
    provider, model = LLMFactory.parse_model_id("ollama:qwen2.5:14b-instruct")

    assert provider == "ollama"
    assert model == "qwen2.5:14b-instruct"


def test_build_messages_matches_provider_chat_shape() -> None:
    """Message helper should expose the exact chat shape used by clients."""
    assert build_messages("system", "user") == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]


def test_parse_model_id_uses_default_provider_for_bare_model(monkeypatch) -> None:
    """Bare model names should use the configured default provider."""
    monkeypatch.setattr(
        "llmkit.llms.factory.get_settings",
        lambda: SimpleNamespace(default_provider="openai"),
    )

    provider, model = LLMFactory.parse_model_id("gpt-5-nano")

    assert provider == "openai"
    assert model == "gpt-5-nano"


def test_openai_client_errors_clearly_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Creating an OpenAI client without an API key should fail clearly."""
    fake_settings = SimpleNamespace(
        temperature=0.2,
        require_openai_api_key=lambda: (_ for _ in ()).throw(
            ValueError("OPENAI_API_KEY is required for provider 'openai'.")
        ),
    )
    monkeypatch.setattr("llmkit.llms.openai_client.get_settings", lambda: fake_settings)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIClient(model="gpt-4.1-mini")


def test_openai_gpt5_payload_omits_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    """GPT-5 family models should not send unsupported custom temperature."""
    fake_settings = SimpleNamespace(
        temperature=0.2,
        require_openai_api_key=lambda: "test-key",
    )
    monkeypatch.setattr("llmkit.llms.openai_client.get_settings", lambda: fake_settings)

    client = OpenAIClient(model="gpt-5-nano")
    payload = client._build_chat_completion_kwargs(
        system="system",
        user="user",
        request_kwargs={},
    )

    assert payload["model"] == "gpt-5-nano"
    assert payload["messages"] == build_messages("system", "user")
    assert "temperature" not in payload


def test_openai_non_gpt5_payload_includes_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-GPT-5 models should keep the configured custom temperature."""
    fake_settings = SimpleNamespace(
        temperature=0.2,
        require_openai_api_key=lambda: "test-key",
    )
    monkeypatch.setattr("llmkit.llms.openai_client.get_settings", lambda: fake_settings)

    client = OpenAIClient(model="gpt-4.1-mini", temperature=0.2)
    payload = client._build_chat_completion_kwargs(
        system="system",
        user="user",
        request_kwargs={},
    )

    assert payload["temperature"] == 0.2


def test_openai_structured_payload_uses_schema_response_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Structured calls should pass the Pydantic schema to OpenAI's parse helper."""
    fake_settings = SimpleNamespace(
        temperature=0.2,
        require_openai_api_key=lambda: "test-key",
    )
    monkeypatch.setattr("llmkit.llms.openai_client.get_settings", lambda: fake_settings)

    parsed = StructuredSmokeOutput(answer="ok", score=0.9)
    fake_completions = FakeParsedCompletions(
        FakeParsedResponse(
            FakeParsedMessage(
                parsed=parsed,
                content='{"answer":"ok","score":0.9}',
            )
        )
    )
    client = OpenAIClient(model="gpt-4.1-mini", temperature=0.2)
    client.client = SimpleNamespace(
        beta=SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions),
        )
    )

    response = client.invoke_structured(
        system="system",
        user="user",
        schema=StructuredSmokeOutput,
    )

    assert fake_completions.kwargs is not None
    assert fake_completions.kwargs["response_format"] is StructuredSmokeOutput
    assert fake_completions.kwargs["messages"] == build_messages("system", "user")
    assert fake_completions.kwargs["temperature"] == 0.2
    assert response.parsed == parsed
    assert response.content == '{"answer":"ok","score":0.9}'
    assert response.usage == {"total_tokens": 7}
    assert response.raw == {"id": "fake-response"}


def test_openai_structured_gpt5_payload_omits_temperature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Structured GPT-5 calls should keep the same temperature behavior as invoke."""
    fake_settings = SimpleNamespace(
        temperature=0.2,
        require_openai_api_key=lambda: "test-key",
    )
    monkeypatch.setattr("llmkit.llms.openai_client.get_settings", lambda: fake_settings)

    fake_completions = FakeParsedCompletions(
        FakeParsedResponse(
            FakeParsedMessage(
                parsed=StructuredSmokeOutput(answer="ok", score=0.9),
                content='{"answer":"ok","score":0.9}',
            )
        )
    )
    client = OpenAIClient(model="gpt-5-nano")
    client.client = SimpleNamespace(
        beta=SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions),
        )
    )

    client.invoke_structured(
        system="system",
        user="user",
        schema=StructuredSmokeOutput,
    )

    assert fake_completions.kwargs is not None
    assert "temperature" not in fake_completions.kwargs


def test_openai_structured_errors_when_parse_returns_no_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing parsed output should fail clearly instead of returning raw JSON."""
    fake_settings = SimpleNamespace(
        temperature=0.2,
        require_openai_api_key=lambda: "test-key",
    )
    monkeypatch.setattr("llmkit.llms.openai_client.get_settings", lambda: fake_settings)

    fake_completions = FakeParsedCompletions(
        FakeParsedResponse(FakeParsedMessage(parsed=None, content="{}"))
    )
    client = OpenAIClient(model="gpt-4.1-mini")
    client.client = SimpleNamespace(
        beta=SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions),
        )
    )

    with pytest.raises(StructuredLLMError, match="did not produce parsed"):
        client.invoke_structured(
            system="system",
            user="user",
            schema=StructuredSmokeOutput,
        )


def test_openai_structured_accepts_closed_nested_list_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Notebook-style structured schemas should use lists, not dynamic maps."""
    fake_settings = SimpleNamespace(
        temperature=0.2,
        require_openai_api_key=lambda: "test-key",
    )
    monkeypatch.setattr("llmkit.llms.openai_client.get_settings", lambda: fake_settings)

    parsed = StructuredExperimentOutput(
        experiment_name="refund policy assistant",
        overall_score=1.0,
        summary_metrics=[
            StructuredMetricOutput(
                name="precision",
                value=0.91,
                target=0.85,
                passed=True,
            )
        ],
    )
    fake_completions = FakeParsedCompletions(
        FakeParsedResponse(
            FakeParsedMessage(
                parsed=parsed,
                content=parsed.model_dump_json(),
            )
        )
    )
    client = OpenAIClient(model="gpt-4.1-mini")
    client.client = SimpleNamespace(
        beta=SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions),
        )
    )

    response = client.invoke_structured(
        system="system",
        user="user",
        schema=StructuredExperimentOutput,
    )

    assert fake_completions.kwargs is not None
    assert fake_completions.kwargs["response_format"] is StructuredExperimentOutput
    assert response.parsed.summary_metrics[0].name == "precision"
