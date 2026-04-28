"""Tests for prompt registry behavior."""

import pytest

from llmkit.prompts import PromptRegistry


def test_prompt_registry_lists_and_gets_prompts() -> None:
    """The registry should expose the initial Release 01 prompts."""
    names = PromptRegistry.list()
    prompt = PromptRegistry.get("chat.basic")

    assert names == [
        "brochure.select_links",
        "brochure.write",
        "chat.basic",
        "classification.structured",
        "research.plan",
        "research.report",
        "research.review",
    ]
    assert "chat.basic" in names
    assert prompt.render_user(topic="paper machines")


def test_prompt_template_errors_on_missing_variable() -> None:
    """Rendering should fail with a clear missing-variable error."""
    prompt = PromptRegistry.get("chat.basic")

    with pytest.raises(ValueError, match="topic"):
        prompt.render_user()


def test_use_case_prompts_exist_and_render() -> None:
    """Business and research prompts should be available for the notebooks."""
    examples = {
        "brochure.select_links": {
            "url": "https://example.com",
            "links": "https://example.com/about",
        },
        "brochure.write": {
            "company_name": "Example Co",
            "url": "https://example.com",
            "content": "Example Co builds useful tools.",
        },
        "research.plan": {
            "question": "Which AI frameworks matter for industrial analytics?",
        },
        "research.report": {
            "question": "Which AI frameworks matter for industrial analytics?",
            "notes": "LangGraph is useful for workflows.",
        },
        "research.review": {
            "question": "Which AI frameworks matter for industrial analytics?",
            "report": "# Report\nLangGraph is useful.",
        },
    }

    for name, variables in examples.items():
        prompt = PromptRegistry.get(name)
        rendered = prompt.render_user(**variables)
        assert rendered


def test_new_prompt_errors_on_missing_variable() -> None:
    """New use-case prompts should keep strict variable validation."""
    prompt = PromptRegistry.get("brochure.write")

    with pytest.raises(ValueError, match="content"):
        prompt.render_user(company_name="Example Co", url="https://example.com")


def test_research_review_prompt_requires_decimal_score() -> None:
    """Reviewer prompt should discourage percent-style scores that fail schema validation."""
    prompt = PromptRegistry.get("research.review")

    assert "0.92, not 92" in prompt.render_user(
        question="Which AI frameworks matter for industrial analytics?",
        report="# Report\nLangGraph is useful.",
    )
    assert "decimal from 0.0 to 1.0" in prompt.system
