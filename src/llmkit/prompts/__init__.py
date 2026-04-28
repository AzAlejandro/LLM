"""Public prompt exports.

Use ``PromptRegistry`` to discover and load reusable prompts. Use
``PromptTemplate`` when defining new registry entries with validated user
variables.
"""

from llmkit.prompts.prompt_template import PromptTemplate
from llmkit.prompts.registry import PromptRegistry

__all__ = ["PromptRegistry", "PromptTemplate"]
