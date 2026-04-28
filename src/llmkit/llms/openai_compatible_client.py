"""Client wrapper for providers exposing an OpenAI-compatible API.

Many hosted and local providers accept the same chat-completions shape as the
OpenAI SDK while using a different base URL and key. This wrapper lets notebooks
use those providers through the same ``invoke`` interface as OpenAI.
"""

from time import perf_counter
from typing import Any

from openai import OpenAI

from llmkit.config.settings import get_settings
from llmkit.llms.base import BaseLLMClient, LLMResponse
from llmkit.llms.messages import build_messages


class OpenAICompatibleClient(BaseLLMClient):
    """Client for OpenAI-compatible providers such as OpenRouter or Groq.

    The provider label is kept separate from the model name so responses can
    still say whether they came from ``openrouter``, ``groq``, ``deepseek``, or a
    generic compatible endpoint.
    """

    def __init__(
        self,
        model: str,
        provider: str = "compatible",
        temperature: float | None = None,
    ) -> None:
        """Create an OpenAI SDK client pointed at a compatible endpoint.

        Args:
            model: Provider-specific model name.
            provider: Toolkit provider label, usually the prefix parsed by
                ``LLMFactory``.
            temperature: Optional default temperature. When omitted, settings
                provide the default.

        Raises:
            ValueError: If ``LLMKIT_OPENAI_COMPATIBLE_API_KEY`` or
                ``LLMKIT_OPENAI_COMPATIBLE_BASE_URL`` is missing.
        """
        settings = get_settings()
        super().__init__(
            model=model,
            provider=provider,
            temperature=settings.temperature if temperature is None else temperature,
        )
        api_key, base_url = settings.require_openai_compatible_config()
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def invoke(self, system: str, user: str, **kwargs: Any) -> LLMResponse:
        """Call the compatible chat endpoint and normalize the response.

        Args:
            system: System instruction controlling persona and output behavior.
            user: Rendered user request.
            **kwargs: Extra chat-completion options forwarded to the compatible
                provider. ``temperature`` overrides the client default.

        Returns:
            Provider-neutral ``LLMResponse`` so notebooks do not depend on the
            compatible provider's raw SDK payload.
        """
        started = perf_counter()
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=kwargs.pop("temperature", self.temperature),
            messages=build_messages(system, user),
            **kwargs,
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
            raw=response.model_dump(),
        )
