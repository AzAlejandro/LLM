"""Public website helper exports.

The web helpers are intentionally small. They support the Release 01 brochure
notebook by fetching one page, extracting basic text, and normalizing links. They
are not a crawler, browser automation layer, or RAG ingestion pipeline.
"""

from llmkit.web.website import (
    fetch_website_contents,
    fetch_website_links,
    normalize_url,
)

__all__ = ["fetch_website_contents", "fetch_website_links", "normalize_url"]
