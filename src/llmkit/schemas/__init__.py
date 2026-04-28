"""Public structured-output schemas and parser.

The schemas in this package are small examples for Release 01. They establish
the pattern for validating JSON returned by a model before downstream code uses
it.
"""

from llmkit.schemas.base import parse_json_output
from llmkit.schemas.llm_outputs import (
    BrochureLink,
    BrochureLinkSelection,
    ClassificationOutput,
    ReportReview,
    ReportData,
    WebSearchItem,
    WebSearchPlan,
)
from llmkit.schemas.rag_outputs import RAGAnswer, RAGChunk, RAGDocument, RetrievedChunk

__all__ = [
    "BrochureLink",
    "BrochureLinkSelection",
    "ClassificationOutput",
    "RAGAnswer",
    "RAGChunk",
    "RAGDocument",
    "ReportData",
    "ReportReview",
    "RetrievedChunk",
    "WebSearchItem",
    "WebSearchPlan",
    "parse_json_output",
]
