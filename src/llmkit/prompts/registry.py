"""Small prompt registry for Release 01.

Prompts live in this single file so they are easy to inspect. The notebooks show
the manual ``system_prompt`` and ``user_prompt`` first, then use this registry to
avoid repeating the same strings. If a prompt is not used by a current notebook,
it should not live here yet.
"""

from llmkit.prompts.prompt_template import PromptTemplate


class PromptRegistry:
    """Read-only registry of prompts used directly by Release 01 notebooks."""

    _prompts: dict[str, PromptTemplate] = {
        "chat.basic": PromptTemplate(
            name="chat.basic",
            description="Basic technical explanation prompt.",
            system="You are a concise technical assistant.",
            user_template="Explain the following topic in practical terms: {topic}",
            required_variables=["topic"],
        ),
        "classification.structured": PromptTemplate(
            name="classification.structured",
            description="Structured request classification prompt.",
            system=(
                "You classify user requests. Return only valid JSON matching "
                "the requested schema."
            ),
            user_template=(
                "Classify this request as one of rag, agent, code, or general. "
                "Return JSON with keys category, confidence, and rationale.\n\n"
                "Request: {request}"
            ),
            required_variables=["request"],
        ),
        "brochure.select_links": PromptTemplate(
            name="brochure.select_links",
            description="Select website links that are useful for a company brochure.",
            system=(
                "You inspect links found on a company website and decide which "
                "links are useful for a business brochure. Keep about, company, "
                "careers, product, customers, and docs links. Ignore privacy, "
                "terms, login, cookie, social media, and email links. Return "
                "only valid JSON matching the requested schema."
            ),
            user_template=(
                "Company website: {url}\n\n"
                "Links found on the site:\n{links}\n\n"
                "Select the links that would help write a brochure about the "
                "company. Return JSON with this shape:\n"
                "{{\"links\": [{{\"type\": \"about page\", \"url\": \"https://...\"}}]}}"
            ),
            required_variables=["url", "links"],
        ),
        "brochure.write": PromptTemplate(
            name="brochure.write",
            description="Write a formal markdown brochure from company website content.",
            system=(
                "You write concise company brochures for prospective customers, "
                "investors, and potential recruits. Use the supplied website "
                "content only. Respond in markdown without code fences. Be "
                "factual, business-oriented, and clear."
            ),
            user_template=(
                "Company name: {company_name}\n"
                "Company website: {url}\n\n"
                "Website content and selected pages:\n{content}\n\n"
                "Create a short brochure in markdown for prospective customers, "
                "investors, and potential recruits."
            ),
            required_variables=["company_name", "url", "content"],
        ),
        "research.plan": PromptTemplate(
            name="research.plan",
            description="Plan a small research workflow as structured JSON.",
            system=(
                "You are a research planner. Given a research question, produce "
                "only valid JSON with a list of search tasks. Each task needs a "
                "reason and a query. Do not perform the research yourself."
            ),
            user_template=(
                "Create a research plan for this question:\n\n{question}\n\n"
                "Return JSON with this shape:\n"
                "{{\"searches\": [{{\"reason\": \"...\", \"query\": \"...\"}}]}}"
            ),
            required_variables=["question"],
        ),
        "research.report": PromptTemplate(
            name="research.report",
            description="Write a markdown report from prepared research notes.",
            system=(
                "You are a senior research writer. You receive a question and "
                "prepared notes. Synthesize them into a clear markdown report "
                "with a short summary, a structured body, and follow-up questions."
            ),
            user_template=(
                "Original question:\n{question}\n\n"
                "Prepared research notes:\n{notes}\n\n"
                "Write a markdown report and include follow-up questions."
            ),
            required_variables=["question", "notes"],
        ),
        "research.review": PromptTemplate(
            name="research.review",
            description="Evaluate a generated research report and suggest follow-up questions.",
            system=(
                "You are a strict report reviewer. Evaluate whether a markdown "
                "report answers the original question, uses the provided notes, "
                "and leaves clear next steps. Return only valid JSON matching "
                "the requested schema. The score must be a decimal from 0.0 "
                "to 1.0, not a percentage or a 1-100 score."
            ),
            user_template=(
                "Original question:\n{question}\n\n"
                "Markdown report:\n{report}\n\n"
                "Return JSON with keys score, passed, feedback, and "
                "follow_up_questions. Use score as a decimal from 0.0 to 1.0. "
                "Example: use 0.92, not 92."
            ),
            required_variables=["question", "report"],
        ),
    }

    @classmethod
    def get(cls, name: str) -> PromptTemplate:
        """Return a registered prompt template by its stable name.

        Args:
            name: Public prompt identifier, for example ``"chat.basic"`` or
                ``"brochure.write"``.

        Returns:
            The matching ``PromptTemplate`` instance. The caller can read its
            ``system`` text directly and call ``render_user`` with the required
            variables to build the user message.

        Raises:
            KeyError: If the prompt name does not exist. The error includes the
                list of registered prompt names so notebooks fail with an
                actionable message instead of a silent fallback.
        """
        try:
            return cls._prompts[name]
        except KeyError as exc:
            available = ", ".join(cls.list())
            raise KeyError(f"Prompt '{name}' was not found. Available: {available}.") from exc

    @classmethod
    def list(cls) -> list[str]:
        """List public prompt names available in this release.

        Returns:
            Sorted prompt identifiers. Sorting keeps notebook output stable and
            makes it easier to compare changes when new prompts are added.
        """
        return sorted(cls._prompts)
