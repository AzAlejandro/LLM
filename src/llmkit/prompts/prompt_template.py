"""Typed prompt template with variable validation.

The toolkit uses this model so prompts are not just loose strings. A prompt has
metadata for humans, a system instruction that controls model behavior, a user
template that receives runtime values, and an explicit list of variables that
must be provided before the template is rendered.
"""

from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """Reusable prompt definition consumed by notebooks and LLM clients.

    Attributes:
        name: Stable registry key, such as ``"chat.basic"``. Code should depend
            on this name instead of importing prompt strings directly.
        description: Human-readable purpose of the prompt. This is for prompt
            selection and documentation; it is not sent to the model.
        system: System message sent to the LLM. This is where the model persona,
            style, boundaries, and response behavior are defined.
        user_template: Format string for the user message. Placeholders are
            rendered with ``render_user`` and should match ``required_variables``.
        required_variables: Names that must be passed to ``render_user``. Missing
            values raise a clear ``ValueError`` before any model call happens.
        version: Lightweight prompt version for notebooks and experiments.
    """

    name: str
    description: str
    system: str
    user_template: str
    required_variables: list[str] = Field(default_factory=list)
    version: str = "1.0.0"

    def render_user(self, **variables: str) -> str:
        """Render the user message after checking required variables.

        Args:
            **variables: Runtime values used by ``str.format`` in
                ``user_template``. For ``chat.basic`` this means passing
                ``topic="..."``; for ``brochure.write`` this means passing
                ``company_name``, ``url``, and ``content``.

        Returns:
            The fully rendered user message ready to pass into
            ``BaseLLMClient.invoke``.

        Raises:
            ValueError: If any required variable is missing or explicitly
                ``None``. This prevents confusing model calls with partially
                rendered prompts.
        """
        missing = [
            variable
            for variable in self.required_variables
            if variable not in variables or variables[variable] is None
        ]
        if missing:
            missing_text = ", ".join(missing)
            raise ValueError(
                f"Prompt '{self.name}' is missing required variables: {missing_text}."
            )
        return self.user_template.format(**variables)
