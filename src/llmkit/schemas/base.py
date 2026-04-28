"""Helpers for converting raw model text into typed Pydantic objects.

Release 01 keeps structured output intentionally small: callers ask the model to
return JSON, then this module parses the raw text and validates it against the
schema chosen by the notebook or application code.
"""

import json
import warnings
from copy import deepcopy
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class StructuredOutputError(ValueError):
    """Raised when raw LLM output cannot be parsed or validated.

    The exception message includes the raw output because malformed model
    responses are common during prompt iteration. Keeping the raw text in the
    error makes notebook debugging faster.
    """


def _resolve_schema_ref(schema_fragment: dict[str, Any], root_schema: dict[str, Any]) -> dict[str, Any]:
    """Resolve a local JSON-schema reference if present."""
    ref = schema_fragment.get("$ref")
    if not ref or not ref.startswith("#/$defs/"):
        return schema_fragment

    definition_name = ref.removeprefix("#/$defs/")
    return root_schema.get("$defs", {}).get(definition_name, schema_fragment)


def _normalize_number_to_range(value: Any, minimum: float | None, maximum: float | None) -> Any:
    """Convert percentage-like numbers into the numeric range requested by a schema."""
    if not isinstance(value, int | float) or isinstance(value, bool):
        return value
    if minimum is None or maximum is None:
        return value

    if maximum <= 1 and 1 < value <= 100:
        return round(value / 100, 6)
    if minimum >= 1 and maximum > 1 and 0 <= value <= 1:
        return round(value * maximum, 6)
    if minimum >= 0 and 1 < maximum <= 10 and maximum < value <= 100:
        return round(value * maximum / 100, 6)
    return value


def _normalize_ranges(data: Any, schema_fragment: dict[str, Any], root_schema: dict[str, Any]) -> Any:
    """Recursively normalize numeric values using JSON-schema minimum/maximum hints."""
    schema_fragment = _resolve_schema_ref(schema_fragment, root_schema)

    if isinstance(data, dict):
        properties = schema_fragment.get("properties", {})
        return {
            key: _normalize_ranges(value, properties.get(key, {}), root_schema)
            for key, value in data.items()
        }

    if isinstance(data, list):
        item_schema = schema_fragment.get("items", {})
        return [_normalize_ranges(item, item_schema, root_schema) for item in data]

    return _normalize_number_to_range(
        data,
        schema_fragment.get("minimum"),
        schema_fragment.get("maximum"),
    )


def _text_from_value(value: Any) -> str:
    """Flatten common free-text fields from model output into a short evidence string."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def _is_number(value: Any) -> bool:
    """Return whether a value is a real numeric score, excluding booleans."""
    return isinstance(value, int | float) and not isinstance(value, bool)


def _adapt_research_quality_eval(data: Any, schema: type[BaseModel]) -> Any:
    """Adapt common LLM evaluation payloads to the local ResearchQualityEval shape."""
    expected_fields = set(schema.model_fields)
    if not {"verdict", "dimensions", "weighted_score"}.issubset(expected_fields):
        return data
    if not isinstance(data, dict):
        return data

    evaluation = data.get("evaluation")
    if not isinstance(evaluation, dict):
        overall = data.get("overall_assessment")
        if not isinstance(overall, dict):
            return data

        weighted_score = overall.get("score", overall.get("score_out_of_5", overall.get("rating_out_of_5")))
        fallback_score = weighted_score
        if not _is_number(fallback_score):
            warnings.warn(
                "Could not adapt ResearchQualityEval: overall_assessment has no numeric score.",
                stacklevel=2,
            )
            return data
        verdict = overall.get("summary", overall.get("comments", data.get("conclusion", "Evaluation completed.")))
        return {
            "verdict": verdict,
            "dimensions": [
                {
                    "name": "clarity",
                    "score": fallback_score,
                    "weight": 0.30,
                    "evidence": _text_from_value(
                        data.get("strengths", data.get("summary", "No evidence provided."))
                    ),
                },
                {
                    "name": "factuality",
                    "score": fallback_score,
                    "weight": 0.45,
                    "evidence": _text_from_value(
                        data.get("factual_accuracy", data.get("references_consistency_and_gaps", "No evidence provided."))
                    ),
                },
                {
                    "name": "actionability",
                    "score": fallback_score,
                    "weight": 0.25,
                    "evidence": _text_from_value(
                        data.get("actionability", data.get("actionable_recommendations", "No evidence provided."))
                    ),
                },
            ],
            "weighted_score": weighted_score,
        }

    non_dimension_keys = {"overall", "overall_assessment"}
    dimension_names = [name for name in ("clarity", "factuality", "actionability") if name in evaluation]
    if not dimension_names:
        dimension_names = [name for name in evaluation if name not in non_dimension_keys]

    default_weights = {
        "clarity": 0.30,
        "factuality": 0.45,
        "actionability": 0.25,
    }
    fallback_weight = 1 / len(dimension_names) if dimension_names else 1

    dimensions = []
    for name in dimension_names:
        item = evaluation.get(name)
        if isinstance(item, dict):
            score = item.get("score", item.get("score_out_of_5"))
            evidence_parts = [
                _text_from_value(item[field])
                for field in ("comments", "notes", "recommendations")
                if field in item
            ]
        elif isinstance(item, int | float) and not isinstance(item, bool):
            score = item
            evidence_parts = [
                _text_from_value(data[field])
                for field in ("strengths", "areas_for_improvement", "actionable_recommendations")
                if field in data
            ]
        else:
            continue
        if not _is_number(score):
            warnings.warn(
                f"Skipping ResearchQualityEval dimension {name!r}: missing numeric score.",
                stacklevel=2,
            )
            continue
        dimensions.append(
            {
                "name": name,
                "score": score,
                "weight": default_weights.get(name, fallback_weight),
                "evidence": " ".join(evidence_parts).strip() or "No evidence provided.",
            }
        )

    overall = evaluation.get("overall", {})
    if isinstance(overall, dict) and overall:
        weighted_score = overall.get("score", overall.get("score_out_of_5"))
        verdict = overall.get("comments", data.get("title", "Evaluation completed."))
    else:
        weighted_score = None
        verdict = evaluation.get(
            "overall_assessment",
            data.get("summary", data.get("title", "Evaluation completed.")),
        )

    if weighted_score is None and dimensions:
        weighted_score = sum(item["score"] * item["weight"] for item in dimensions)
    if not dimensions or not _is_number(weighted_score):
        warnings.warn(
            "Could not adapt ResearchQualityEval: output lacks enough numeric scores.",
            stacklevel=2,
        )
        return data

    return {
        "verdict": verdict,
        "dimensions": dimensions,
        "weighted_score": weighted_score,
    }


def _normalize_model_output(data: Any, schema: type[BaseModel]) -> Any:
    """Apply conservative repairs to common schema-adjacent model outputs."""
    root_schema = schema.model_json_schema()
    adapted = _adapt_research_quality_eval(data, schema)
    return _normalize_ranges(adapted, root_schema, root_schema)


def _normalization_candidates(data: Any, schema: type[BaseModel]) -> list[Any]:
    """Return original and normalized candidates without surfacing repair errors."""
    candidates = [data]
    try:
        normalized = _normalize_model_output(deepcopy(data), schema)
    except Exception as exc:  # pragma: no cover - defensive guard for notebooks
        warnings.warn(
            f"Could not normalize output for schema {schema.__name__}: {exc}",
            stacklevel=2,
        )
        return candidates

    if normalized != data:
        candidates.append(normalized)
    return candidates


def parse_json_output(raw_text: str, schema: type[SchemaT]) -> SchemaT:
    """Parse JSON text and validate it against a Pydantic schema.

    Args:
        raw_text: Exact text returned by the model. It must be valid JSON, not
            markdown-wrapped JSON or explanatory prose.
        schema: Pydantic model class that defines the expected output contract.

    Returns:
        An instance of ``schema`` with typed and validated fields.

    Raises:
        StructuredOutputError: If ``raw_text`` is not valid JSON or if the parsed
            object does not satisfy the schema.
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise StructuredOutputError(
            f"Output is not valid JSON. Raw output: {raw_text}"
        ) from exc

    for candidate in _normalization_candidates(data, schema):
        try:
            return schema.model_validate(candidate)
        except ValidationError as exc:
            validation_error = exc

    warnings.warn(
        f"Output does not match schema {schema.__name__}; raising StructuredOutputError.",
        stacklevel=2,
    )
    raise StructuredOutputError(
        f"Output does not match schema {schema.__name__}. Raw output: {raw_text}"
    ) from validation_error
