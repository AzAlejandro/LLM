"""Tests for centralized settings."""

from llmkit.config.settings import Settings


def test_settings_load_defaults_without_api_key(monkeypatch) -> None:
    """Settings should have useful defaults and not require API keys at import."""
    monkeypatch.delenv("LLMKIT_DEFAULT_PROVIDER", raising=False)
    monkeypatch.delenv("LLMKIT_DEFAULT_MODEL", raising=False)
    monkeypatch.delenv("LLMKIT_OLLAMA_BASE_URL", raising=False)
    loaded = Settings(_env_file=None)

    assert loaded.default_provider == "openai"
    assert loaded.default_model == "gpt-5.4-nano"
    assert loaded.ollama_base_url == "http://localhost:11434"
    assert loaded.knowledge_base_dir.as_posix() == "data/knowledge_base"
    assert loaded.vectorstore_dir.as_posix() == "data/vectorstores"
    assert loaded.openai_embedding_model == "text-embedding-3-large"
