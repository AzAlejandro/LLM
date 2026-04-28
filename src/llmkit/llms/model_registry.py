"""Initial model metadata catalog for Release 01.

The runtime factory does not need advanced model metadata yet, but this registry
keeps a small source of truth for known model ids and their basic capabilities.
Later releases can expand this into model selection, evaluation, or UI metadata
without changing the public ``provider:model`` naming convention.

Pricing values are reference metadata for notebook guidance, not billing logic.
They should be checked against the official OpenAI pricing page before making
budget decisions because model prices and available variants can change.
"""

from pydantic import BaseModel


class ModelInfo(BaseModel):
    """Metadata describing one known model option.

    Attributes:
        provider: Provider prefix used in model ids and response metadata.
        model: Provider-specific model name.
        description: Short usage note for humans choosing a model.
        is_local: Whether the model is expected to run locally.
        supports_structured_output: Whether the model is known to support more
            reliable structured-output behavior.
        supports_tools: Whether the model is known to support tool calling. This
            is recorded for future releases but not used by Release 01 clients.
        context_window_tokens: Maximum context window when published by the
            provider docs.
        max_output_tokens: Maximum output tokens when published by the provider
            docs.
        input_price_per_1m_tokens_usd: Standard API input-token price in USD per
            1M tokens, when available.
        cached_input_price_per_1m_tokens_usd: Standard API cached-input price in
            USD per 1M tokens, when available.
        output_price_per_1m_tokens_usd: Standard API output-token price in USD
            per 1M tokens, when available.
    """

    provider: str
    model: str
    description: str
    is_local: bool = False
    supports_structured_output: bool = False
    supports_tools: bool = False
    context_window_tokens: int | None = None
    max_output_tokens: int | None = None
    input_price_per_1m_tokens_usd: float | None = None
    cached_input_price_per_1m_tokens_usd: float | None = None
    output_price_per_1m_tokens_usd: float | None = None


MODEL_REGISTRY: dict[str, ModelInfo] = {
    "openai:gpt-5.4-nano": ModelInfo(
        provider="openai",
        model="gpt-5.4-nano",
        description="Cheapest GPT-5.4-class model for simple high-volume tasks.",
        supports_structured_output=True,
        supports_tools=True,
        context_window_tokens=400_000,
        max_output_tokens=128_000,
        input_price_per_1m_tokens_usd=0.20,
        cached_input_price_per_1m_tokens_usd=0.02,
        output_price_per_1m_tokens_usd=1.25,
    ),
    "openai:gpt-5.4-mini": ModelInfo(
        provider="openai",
        model="gpt-5.4-mini",
        description="Stronger small GPT-5.4 model for coding and subagent tasks.",
        supports_structured_output=True,
        supports_tools=True,
        context_window_tokens=400_000,
        max_output_tokens=128_000,
        input_price_per_1m_tokens_usd=0.75,
        cached_input_price_per_1m_tokens_usd=0.075,
        output_price_per_1m_tokens_usd=4.50,
    ),
    "openai:gpt-5-nano": ModelInfo(
        provider="openai",
        model="gpt-5-nano",
        description="Fastest and cheapest GPT-5 model; good for classification and summaries.",
        supports_structured_output=True,
        supports_tools=True,
        context_window_tokens=400_000,
        max_output_tokens=128_000,
        input_price_per_1m_tokens_usd=0.05,
        cached_input_price_per_1m_tokens_usd=0.005,
        output_price_per_1m_tokens_usd=0.40,
    ),
    "openai:gpt-4.1-mini": ModelInfo(
        provider="openai",
        model="gpt-4.1-mini",
        description="Older GPT-4.1 small model kept as a compatibility example.",
        supports_structured_output=True,
        supports_tools=True,
    ),
    "openai:gpt-4.1-nano": ModelInfo(
        provider="openai",
        model="gpt-4.1-nano",
        description="Older GPT-4.1 low-cost model kept as a compatibility example.",
        supports_structured_output=True,
    ),
    "ollama:qwen2.5:14b-instruct": ModelInfo(
        provider="ollama",
        model="qwen2.5:14b-instruct",
        description="Local Ollama instruction model example.",
        is_local=True,
    ),
}
