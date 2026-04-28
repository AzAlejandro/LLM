"""Factory for constructing LLM clients from simple model identifiers.

The factory is the main entry point notebooks should use when they need a model.
It keeps provider selection out of notebooks and lets callers switch from
``openai:gpt-5.4-nano`` to ``ollama:qwen2.5:14b-instruct`` without changing the
rest of the prompt or response handling code. It also accepts bare model names
such as ``gpt-5-nano`` and pairs them with ``settings.default_provider``.
"""

from llmkit.config.settings import get_settings
from llmkit.llms.base import BaseLLMClient


class LLMFactory:
    """Create concrete LLM clients from model identifiers.

    Supported providers in Release 01:
        ``openai`` creates ``OpenAIClient`` and requires ``OPENAI_API_KEY``.
        ``ollama`` creates ``OllamaClient`` and uses ``LLMKIT_OLLAMA_BASE_URL``.
        ``openrouter``, ``groq``, ``deepseek``, and ``compatible`` create an
        ``OpenAICompatibleClient`` using the compatible API settings.

    Preferred explicit format is ``provider:model``. Bare model names are also
    accepted and use ``settings.default_provider``. The model part may itself
    contain colons. This matters for Ollama model identifiers such as
    ``qwen2.5:14b-instruct``.
    """

    COMPATIBLE_PROVIDERS = {"openrouter", "groq", "deepseek", "compatible"}

    @staticmethod
    def parse_model_id(model_id: str | None = None) -> tuple[str, str]:
        """Split a model identifier into provider and model name.

        Args:
            model_id: Optional identifier. Use ``provider:model`` for explicit
                provider selection, or a bare model name such as ``gpt-5-nano``
                to pair it with ``settings.default_provider``. If omitted, the
                default provider and model from settings are used.

        Returns:
            Tuple ``(provider, model)``. Only the first colon is treated as the
            separator so model names can contain additional colons.

        Raises:
            ValueError: If an explicit provider prefix is present but either
                provider or model is empty.
        """
        if model_id is None:
            settings = get_settings()
            return settings.default_provider, settings.default_model
        if ":" not in model_id:
            return get_settings().default_provider, model_id
        provider, model = model_id.split(":", 1)
        if not provider or not model:
            raise ValueError("model_id must include both provider and model.")
        return provider, model

    @classmethod
    def create(cls, model_id: str | None = None) -> BaseLLMClient:
        """Instantiate the concrete client for a model identifier.

        Args:
            model_id: Optional model identifier. Use ``provider:model`` to select
                a provider explicitly, use a bare model name with the default
                provider, or omit it to use both configured defaults.

        Returns:
            A concrete ``BaseLLMClient`` subclass ready to call with ``invoke``.

        Raises:
            ValueError: If the provider prefix is not supported.
            ValueError: From the selected client when required configuration,
                such as an API key, is missing.
        """
        provider, model = cls.parse_model_id(model_id)
        if provider == "openai":
            from llmkit.llms.openai_client import OpenAIClient

            return OpenAIClient(model=model)
        if provider == "ollama":
            from llmkit.llms.ollama_client import OllamaClient

            return OllamaClient(model=model)
        if provider in cls.COMPATIBLE_PROVIDERS:
            from llmkit.llms.openai_compatible_client import OpenAICompatibleClient

            return OpenAICompatibleClient(model=model, provider=provider)
        raise ValueError(f"Unsupported provider '{provider}'.")
