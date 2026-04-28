"""Release 01 package for the local LLM toolkit.

The package exposes a small reusable foundation for notebooks: centralized
settings, provider-neutral LLM clients, prompt templates, a prompt registry, and
Pydantic schemas for structured outputs. Later releases should build on this
surface instead of duplicating setup code in notebooks.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
