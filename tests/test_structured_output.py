"""Tests for structured output parsing."""

import pytest
from pydantic import BaseModel, Field

from llmkit.schemas import (
    BrochureLinkSelection,
    ClassificationOutput,
    ReportReview,
    WebSearchPlan,
    parse_json_output,
)
from llmkit.schemas.base import StructuredOutputError


def test_parse_json_output_validates_classification() -> None:
    """Valid JSON should parse into the requested Pydantic schema."""
    parsed = parse_json_output(
        '{"category": "rag", "confidence": 0.91, "rationale": "Needs retrieval."}',
        ClassificationOutput,
    )

    assert parsed.category == "rag"
    assert parsed.confidence == 0.91


def test_parse_json_output_preserves_raw_text_on_error() -> None:
    """Invalid JSON should raise a useful error containing the raw output."""
    with pytest.raises(StructuredOutputError, match="not json"):
        parse_json_output("not json", ClassificationOutput)


def test_parse_json_output_validates_brochure_links() -> None:
    """Brochure link selection should parse into typed Pydantic objects."""
    parsed = parse_json_output(
        (
            '{"links": ['
            '{"type": "about page", "url": "https://example.com/about"}'
            "]}"
        ),
        BrochureLinkSelection,
    )

    assert parsed.links[0].type == "about page"
    assert parsed.links[0].url == "https://example.com/about"


def test_parse_json_output_validates_research_plan_and_review() -> None:
    """Research workflow schemas should validate planner and reviewer outputs."""
    plan = parse_json_output(
        (
            '{"searches": ['
            '{"reason": "Find current frameworks.", "query": "agent frameworks 2026"}'
            "]}"
        ),
        WebSearchPlan,
    )
    review = parse_json_output(
        (
            '{"score": 0.82, "passed": true, "feedback": "Useful draft.", '
            '"follow_up_questions": ["Which framework is easiest to deploy?"]}'
        ),
        ReportReview,
    )

    assert plan.searches[0].query == "agent frameworks 2026"
    assert review.passed is True


def test_parse_json_output_normalizes_percentage_score() -> None:
    """Percent-like scores should normalize to schemas that expect 0 to 1."""
    review = parse_json_output(
        (
            '{"score": 92, "passed": true, "feedback": "Useful draft.", '
            '"follow_up_questions": ["Which framework is easiest to deploy?"]}'
        ),
        ReportReview,
    )

    assert review.score == 0.92


class EvaluationDimension(BaseModel):
    """One local notebook-style quality dimension."""

    name: str
    score: float = Field(ge=1, le=5)
    weight: float = Field(ge=0, le=1)
    evidence: str


class ResearchQualityEval(BaseModel):
    """Notebook-style quality evaluation contract."""

    verdict: str
    dimensions: list[EvaluationDimension]
    weighted_score: float = Field(ge=1, le=5)


def test_parse_json_output_adapts_nested_research_quality_eval() -> None:
    """Common nested evaluator JSON should adapt to the local quality schema."""
    parsed = parse_json_output(
        (
            '{"title": "Evaluation", "evaluation": {'
            '"overall": {"score_out_of_5": 3.9, "comments": "Strong structure."},'
            '"clarity": {"score_out_of_5": 4, "notes": ["Clear sections."]},'
            '"factuality": {"score_out_of_5": 3, "notes": ["Needs sources."]},'
            '"actionability": {"score_out_of_5": 4, "recommendations": ["Add rubric."]}'
            "}}"
        ),
        ResearchQualityEval,
    )

    assert parsed.verdict == "Strong structure."
    assert parsed.weighted_score == 3.9
    assert [dimension.name for dimension in parsed.dimensions] == [
        "clarity",
        "factuality",
        "actionability",
    ]
    assert parsed.dimensions[0].score == 4


def test_parse_json_output_adapts_decimal_dimension_scores() -> None:
    """Decimal dimension scores should scale into the schema's requested range."""
    parsed = parse_json_output(
        (
            '{"summary": "Evaluation summary.", "evaluation": {'
            '"clarity": 0.92,'
            '"factuality": 0.78,'
            '"actionability": 0.93,'
            '"overall_assessment": "Clear and useful, with a few gaps."'
            '}, "strengths": ["Clear structure."], '
            '"areas_for_improvement": ["Add KPIs."], '
            '"actionable_recommendations": ["Create a rubric."]}'
        ),
        ResearchQualityEval,
    )

    assert parsed.verdict == "Clear and useful, with a few gaps."
    assert parsed.dimensions[0].score == 4.6
    assert parsed.dimensions[1].score == 3.9
    assert parsed.dimensions[2].score == 4.65
    assert parsed.weighted_score == pytest.approx(4.2975)


def test_parse_json_output_adapts_top_level_quality_eval() -> None:
    """Top-level assessment payloads should adapt to the local quality schema."""
    parsed = parse_json_output(
        (
            '{"report_title": "Evaluating AI Agent Frameworks", '
            '"overall_assessment": {'
            '"rating_out_of_5": 4.0, '
            '"summary": "Clear, practical, and deployment-focused."'
            '}, '
            '"strengths": ["Structured, deployment-oriented framing."], '
            '"factual_accuracy": {"observations": ["Appropriate industrial references."]}, '
            '"actionability": {"short_term_recommendations": ["Define a scoring rubric."]}, '
            '"conclusion": "Solid and actionable."}'
        ),
        ResearchQualityEval,
    )

    assert parsed.verdict == "Clear, practical, and deployment-focused."
    assert parsed.weighted_score == 4.0
    assert [dimension.name for dimension in parsed.dimensions] == [
        "clarity",
        "factuality",
        "actionability",
    ]
    assert all(dimension.score == 4.0 for dimension in parsed.dimensions)


def test_parse_json_output_warns_when_quality_eval_cannot_be_adapted() -> None:
    """Malformed quality eval variants should warn instead of crashing internally."""
    raw_json = (
        '{"evaluation": {'
        '"clarity": {"notes": ["Clear but no score."]},'
        '"factuality": {"notes": ["Needs sources but no score."]},'
        '"actionability": {"recommendations": ["Add rubric but no score."]}'
        "}}"
    )

    with pytest.warns(UserWarning) as warnings_record:
        with pytest.raises(StructuredOutputError):
            parse_json_output(raw_json, ResearchQualityEval)

    warning_messages = [str(warning.message) for warning in warnings_record]
    assert any("numeric score" in message for message in warning_messages)
    assert any("does not match schema" in message for message in warning_messages)
