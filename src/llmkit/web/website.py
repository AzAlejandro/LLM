"""Small website helpers for the brochure notebook.

These functions provide the minimum web extraction needed for Release 01:
download one HTML page, extract visible-ish text, and collect links. The goal is
to support a business use case without introducing a crawler, headless browser,
cache, queue, or full document pipeline.
"""

from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag, urlparse

import httpx


class _WebsiteHTMLParser(HTMLParser):
    """Collect basic text and links from an HTML document.

    The parser deliberately ignores scripts, styles, and metadata. It is not
    meant to perfectly reproduce browser-visible text; it is a lightweight
    extractor for demos and small notebooks.
    """

    def __init__(self) -> None:
        """Initialize parser state for links and text collection."""
        super().__init__()
        self.links: list[str] = []
        self.text_parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect ``href`` values and track ignored HTML sections."""
        if tag in {"script", "style", "noscript", "svg", "meta"}:
            self._ignored_depth += 1
            return
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                self.links.append(value.strip())

    def handle_endtag(self, tag: str) -> None:
        """Leave ignored sections when closing tags are encountered."""
        if tag in {"script", "style", "noscript", "svg", "meta"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        """Collect non-empty text outside ignored sections."""
        if self._ignored_depth:
            return
        text = " ".join(data.split())
        if text:
            self.text_parts.append(text)


def normalize_url(base_url: str, href: str) -> str | None:
    """Convert a page link into a clean absolute HTTP(S) URL.

    Args:
        base_url: URL of the page where the link was found.
        href: Raw link value from an ``href`` attribute. It may be absolute,
            relative, an anchor, an email link, or another unsupported scheme.

    Returns:
        Absolute URL without a fragment, or ``None`` when the link should be
        ignored for the Release 01 brochure flow.
    """
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    absolute = urljoin(base_url, href)
    absolute, _fragment = urldefrag(absolute)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return absolute


def _fetch_html(url: str, timeout: float = 20.0) -> str:
    """Fetch raw HTML and raise a clear error if the request fails."""
    try:
        response = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "llmkit-release-01/0.1"},
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ConnectionError(f"Could not fetch website URL: {url}") from exc
    return response.text


def fetch_website_links(url: str, limit: int = 80) -> list[str]:
    """Fetch a page and return normalized links found in its HTML.

    Args:
        url: Page URL to inspect.
        limit: Maximum number of unique links to return. This keeps notebook
            prompts small and prevents accidental huge prompts on link-heavy
            pages.

    Returns:
        Ordered list of unique absolute HTTP(S) URLs.
    """
    parser = _WebsiteHTMLParser()
    parser.feed(_fetch_html(url))

    seen: set[str] = set()
    links: list[str] = []
    for href in parser.links:
        normalized = normalize_url(url, href)
        if normalized and normalized not in seen:
            seen.add(normalized)
            links.append(normalized)
        if len(links) >= limit:
            break
    return links


def fetch_website_contents(url: str, max_chars: int = 5_000) -> str:
    """Fetch a page and return compact text for LLM prompting.

    Args:
        url: Page URL to fetch.
        max_chars: Character cap applied after text extraction. This keeps
            Release 01 examples predictable and avoids overlong prompts.

    Returns:
        Extracted text prefixed with the source URL.
    """
    parser = _WebsiteHTMLParser()
    parser.feed(_fetch_html(url))
    text = "\n".join(parser.text_parts)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[truncated]"
    return f"Source URL: {url}\n\n{text}"
