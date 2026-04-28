"""Centralized runtime settings for the toolkit.

This module is the only place that reads environment variables directly.
Everything else imports ``settings`` or receives values from objects created by
factories and helpers. Keeping configuration here prevents notebooks and
clients from scattering ``os.getenv`` calls across the project.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed configuration for providers and local paths.

    Attributes:
        default_provider: Provider used when ``LLMFactory.create`` is called
            without an explicit model id.
        default_model: Model used with ``default_provider``. The default favors
            a current low-cost OpenAI model suitable for smoke tests.
        temperature: Default generation temperature shared by clients unless a
            call overrides it.
        data_dir: Local data folder reserved for later releases and notebooks.
        log_dir: Folder used by ``configure_logging`` when file logging is
            enabled.
        openai_api_key: Secret for the official OpenAI API. It is optional at
            settings-load time so local-only tests can run without credentials.
        openai_compatible_api_key: Secret for compatible providers such as
            OpenRouter, Groq, DeepSeek, or self-hosted OpenAI-compatible APIs.
        openai_compatible_base_url: Base URL for compatible providers.
        ollama_base_url: Local Ollama server URL.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    default_provider: str = Field(default="openai", alias="LLMKIT_DEFAULT_PROVIDER")
    default_model: str = Field(default="gpt-5.4-nano", alias="LLMKIT_DEFAULT_MODEL")
    temperature: float = Field(default=0.2, alias="LLMKIT_TEMPERATURE")
    data_dir: Path = Field(default=Path("data"), alias="LLMKIT_DATA_DIR")
    log_dir: Path = Field(default=Path("logs"), alias="LLMKIT_LOG_DIR")
    knowledge_base_dir: Path = Field(
        default=Path("data/knowledge_base"),
        alias="LLMKIT_KNOWLEDGE_BASE_DIR",
    )
    vectorstore_dir: Path = Field(
        default=Path("data/vectorstores"),
        alias="LLMKIT_VECTORSTORE_DIR",
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-large",
        alias="LLMKIT_OPENAI_EMBEDDING_MODEL",
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_compatible_api_key: str | None = Field(
        default=None,
        alias="LLMKIT_OPENAI_COMPATIBLE_API_KEY",
    )
    openai_compatible_base_url: str | None = Field(
        default=None,
        alias="LLMKIT_OPENAI_COMPATIBLE_BASE_URL",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        alias="LLMKIT_OLLAMA_BASE_URL",
    )

    def require_openai_api_key(self) -> str:
        """Return the OpenAI API key for calls that actually need OpenAI.

        Settings can be imported without credentials, but constructing an
        OpenAI-backed client must fail early when ``OPENAI_API_KEY`` is missing.

        Raises:
            ValueError: If ``OPENAI_API_KEY`` is empty or unset.
        """
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for provider 'openai'.")
        return self.openai_api_key

    def require_openai_compatible_config(self) -> tuple[str, str]:
        """Return API key and base URL for OpenAI-compatible providers.

        This method is used by ``OpenAICompatibleClient`` so provider wrappers do
        not need to know which environment variable stores each value.

        Raises:
            ValueError: If either the compatible API key or base URL is missing.
        """
        if not self.openai_compatible_api_key:
            raise ValueError(
                "LLMKIT_OPENAI_COMPATIBLE_API_KEY is required for compatible providers."
            )
        if not self.openai_compatible_base_url:
            raise ValueError(
                "LLMKIT_OPENAI_COMPATIBLE_BASE_URL is required for compatible providers."
            )
        return self.openai_compatible_api_key, self.openai_compatible_base_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once and reuse the same object across imports.

    Returns:
        A cached ``Settings`` instance populated from defaults, environment
        variables, and ``.env`` when present.
    """
    return Settings()


settings = get_settings()
