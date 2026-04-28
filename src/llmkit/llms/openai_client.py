"""Client wrapper for the official OpenAI API.

The wrapper keeps OpenAI SDK details out of notebooks. Callers pass a system
message and a rendered user message, then receive the toolkit's normalized
``LLMResponse`` instead of an SDK-specific object.
"""

from time import perf_counter
from typing import Any

from openai import OpenAI
from pydantic import BaseModel

from llmkit.config.settings import get_settings
from llmkit.llms.base import (
    BaseLLMClient,
    LLMResponse,
    SchemaT,
    StructuredLLMError,
    StructuredLLMResponse,
)
from llmkit.llms.messages import build_messages


def _dump_sdk_model(model: Any) -> Any:
    """Serialize SDK models while suppressing warnings from parsed Pydantic fields."""
    try:
        return model.model_dump(mode="json", warnings=False)
    except TypeError:
        return model.model_dump()


class OpenAIClient(BaseLLMClient):
    """OpenAI chat-completions client used by ``LLMFactory``.

    The client reads ``OPENAI_API_KEY`` through centralized settings during
    construction. This means importing the toolkit does not require credentials,
    but creating an OpenAI client fails early with a clear error if the key is
    missing.
    """

    def __init__(self, model: str, temperature: float | None = None) -> None:
        """Create a configured OpenAI SDK client.

        Args:
            model: OpenAI model name, for example ``"gpt-5.4-nano"``.
            temperature: Optional default temperature for this client. When
                omitted, ``LLMKIT_TEMPERATURE`` from settings is used.

        Raises:
            ValueError: If ``OPENAI_API_KEY`` is missing.
        """
        settings = get_settings()
        super().__init__(
            model=model,
            provider="openai",
            temperature=settings.temperature if temperature is None else temperature,
        )
        self.client = OpenAI(api_key=settings.require_openai_api_key())

    def _supports_custom_temperature(self) -> bool:
        """Return whether this OpenAI model accepts a custom temperature value.

        Some current OpenAI reasoning models only accept the API default
        temperature. Sending ``temperature=0.2`` to those models raises a
        ``BadRequestError`` before generation starts. The client treats GPT-5
        family models as default-temperature models and omits the parameter.
        """
        return not self.model.startswith("gpt-5")

    def _build_chat_completion_kwargs(
        self,
        system: str,
        user: str,
        request_kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Build OpenAI chat-completion arguments for one invocation.

        Args:
            system: System instruction controlling persona and constraints.
            user: Rendered user message.
            request_kwargs: Extra caller-provided OpenAI request options.

        Returns:
            Keyword arguments ready for ``client.chat.completions.create``.

        Notes:
            ``temperature`` is only included for models that support custom
            temperature. For GPT-5 family models, the parameter is deliberately
            omitted so the API uses its required default.
        """
        kwargs = dict(request_kwargs)
        temperature = kwargs.pop("temperature", self.temperature)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": build_messages(system, user),
        }
        if self._supports_custom_temperature():
            payload["temperature"] = temperature
        payload.update(kwargs)
        return payload

    def invoke(self, system: str, user: str, **kwargs: Any) -> LLMResponse:
        """Call OpenAI chat completions and normalize the response.

        Args:
            system: System instruction controlling persona, style, and output
                constraints.
            user: Rendered user request.
            **kwargs: Extra OpenAI chat-completion parameters. ``temperature``
                can be supplied here to override the client default for models
                that support custom temperature. GPT-5 family models use the API
                default temperature because custom values are rejected.

        Returns:
            ``LLMResponse`` with generated content, provider metadata, latency,
            token usage when available, and the raw response as a dictionary.
        """
        started = perf_counter()
        response = self.client.chat.completions.create(
            **self._build_chat_completion_kwargs(system, user, kwargs),
        )
        latency = perf_counter() - started
        content = response.choices[0].message.content or ""
        usage = response.usage.model_dump() if response.usage else None
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            latency_seconds=latency,
            usage=usage,
            raw=_dump_sdk_model(response),
        )

    def invoke_structured(
        self,
        system: str,
        user: str,
        schema: type[SchemaT],
        **kwargs: Any,
    ) -> StructuredLLMResponse[SchemaT]:
        """Call OpenAI with native structured output enforced by Pydantic.

        Args:
            system: System instruction controlling persona, style, and task.
            user: Rendered user request.
            schema: Pydantic model class that defines the output contract.
            **kwargs: Extra OpenAI chat-completion parameters. ``response_format``
                is reserved for ``schema`` and must not be supplied directly.

        Returns:
            ``StructuredLLMResponse`` containing the parsed Pydantic object and
            provider metadata.

        Raises:
            TypeError: If ``schema`` is not a Pydantic model class.
            StructuredLLMError: If OpenAI returns no parsed object or refuses.
        """
        if not isinstance(schema, type) or not issubclass(schema, BaseModel):
            raise TypeError("schema must be a Pydantic BaseModel class.")
        if "response_format" in kwargs:
            raise ValueError("Use schema=... instead of response_format for invoke_structured().")

        payload = self._build_chat_completion_kwargs(system, user, kwargs)
        payload["response_format"] = schema

        started = perf_counter()
        response = self.client.beta.chat.completions.parse(**payload)
        latency = perf_counter() - started

        message = response.choices[0].message
        refusal = getattr(message, "refusal", None)
        if refusal:
            raise StructuredLLMError(f"OpenAI refused structured output: {refusal}")

        parsed = message.parsed
        if parsed is None:
            raise StructuredLLMError(
                f"OpenAI structured output did not produce parsed {schema.__name__}."
            )

        content = message.content or parsed.model_dump_json()
        usage = response.usage.model_dump() if response.usage else None
        return StructuredLLMResponse(
            parsed=parsed,
            content=content,
            model=self.model,
            provider=self.provider,
            latency_seconds=latency,
            usage=usage,
            raw=_dump_sdk_model(response),
        )
