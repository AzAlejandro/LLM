"""Client wrapper for local Ollama chat models.

Ollama is handled separately from OpenAI-compatible providers because local
setups usually need clearer connection errors and the native ``/api/chat``
payload shape. The public calling surface still matches the other clients.
"""

from time import perf_counter
from typing import Any

import httpx

from llmkit.config.settings import get_settings
from llmkit.llms.base import BaseLLMClient, LLMResponse
from llmkit.llms.messages import build_messages


class OllamaClient(BaseLLMClient):
    """Local chat client for models served by Ollama.

    The client uses ``LLMKIT_OLLAMA_BASE_URL`` from settings and does not require
    an API key. It is useful for Release 01 smoke tests where a remote provider
    should remain optional.
    """

    def __init__(self, model: str, temperature: float | None = None) -> None:
        """Create a local Ollama client.

        Args:
            model: Ollama model name, for example ``"qwen2.5:14b-instruct"``.
            temperature: Optional default temperature. When omitted, settings
                provide the default.
        """
        settings = get_settings()
        super().__init__(
            model=model,
            provider="ollama",
            temperature=settings.temperature if temperature is None else temperature,
        )
        self.base_url = settings.ollama_base_url.rstrip("/")

    def invoke(self, system: str, user: str, **kwargs: Any) -> LLMResponse:
        """Call Ollama ``/api/chat`` and normalize the response.

        Args:
            system: System instruction sent as the first chat message.
            user: Rendered user request sent as the second chat message.
            **kwargs: Extra values merged into the Ollama JSON payload.
                ``temperature`` is placed inside the ``options`` block.

        Returns:
            ``LLMResponse`` with content, latency, local evaluation counters when
            returned by Ollama, and the raw JSON payload.

        Raises:
            ConnectionError: If the configured Ollama server cannot be reached or
                returns an HTTP error.
        """
        started = perf_counter()
        payload = {
            "model": self.model,
            "stream": False,
            "messages": build_messages(system, user),
            "options": {"temperature": kwargs.pop("temperature", self.temperature)},
        }
        payload.update(kwargs)

        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectionError(
                f"Could not call Ollama at {self.base_url}. Is Ollama running?"
            ) from exc

        latency = perf_counter() - started
        data = response.json()
        content = data.get("message", {}).get("content", "")
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            latency_seconds=latency,
            usage={
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
            },
            raw=data,
        )
