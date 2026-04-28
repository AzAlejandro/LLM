"""Pydantic schemas for the first structured-output examples.

These schemas are intentionally small. They demonstrate the core pattern needed
later by routers, evaluators, and graph nodes: ask for JSON, parse it, and reject
responses that do not match the expected shape.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ClassificationOutput(BaseModel):
    """Schema for routing a user request into a coarse toolkit category.

    Attributes:
        category: One of the initial Release 01 categories. These labels prepare
            later releases for routing into RAG, agent, code, or general flows.
        confidence: Model confidence from 0 to 1.
        rationale: Short explanation supporting the selected category.
    """

    category: Literal["rag", "agent", "code", "general"]
    confidence: float = Field(ge=0, le=1)
    rationale: str


class WebSearchItem(BaseModel):
    """One planned research/search task.

    Attributes:
        reason: Why this search task matters for the original question.
        query: Search query text a later tool or human researcher should run.
    """

    reason: str = Field(description="Why this search is important.")
    query: str = Field(description="Search query to run.")


class WebSearchPlan(BaseModel):
    """Structured plan for a small research workflow.

    Attributes:
        searches: Ordered list of research/search tasks. Release 01 does not
            execute web search tools; this schema prepares the plan that a later
            tool-enabled release could run.
    """

    searches: list[WebSearchItem]


class ReportData(BaseModel):
    """Structured report payload produced from prepared research notes.

    Attributes:
        short_summary: Brief executive summary.
        markdown_report: Full report in markdown.
        follow_up_questions: Suggested next questions to research.
    """

    short_summary: str
    markdown_report: str
    follow_up_questions: list[str]


class BrochureLink(BaseModel):
    """One website link selected as useful for a company brochure.

    Attributes:
        type: Human-readable label such as ``"about page"`` or
            ``"careers page"``.
        url: Absolute HTTP(S) URL for the selected page.
    """

    type: str
    url: str


class BrochureLinkSelection(BaseModel):
    """Structured output for the brochure link-selection step.

    Attributes:
        links: Links the model judged useful for brochure generation. The
            notebook uses these links to fetch additional page content.
    """

    links: list[BrochureLink]


class ReportReview(BaseModel):
    """Structured review of a generated research report.

    Attributes:
        score: Quality score from 0 to 1.
        passed: Whether the report is good enough to use.
        feedback: Specific critique or improvement guidance.
        follow_up_questions: Questions worth investigating next.
    """

    score: float = Field(ge=0, le=1)
    passed: bool
    feedback: str
    follow_up_questions: list[str]
