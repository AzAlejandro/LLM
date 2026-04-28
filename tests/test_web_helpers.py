"""Tests for lightweight website helpers."""

from llmkit.web import fetch_website_contents, fetch_website_links, normalize_url


def test_normalize_url_filters_and_resolves_links() -> None:
    """Relative links should become absolute and unsupported schemes should drop."""
    assert normalize_url("https://example.com/base/", "/about#team") == (
        "https://example.com/about"
    )
    assert normalize_url("https://example.com", "mailto:test@example.com") is None
    assert normalize_url("https://example.com", "#section") is None


def test_fetch_website_links_with_local_html(monkeypatch) -> None:
    """Link extraction should work against simple HTML without internet."""
    html = """
    <html>
      <body>
        <a href="/about">About</a>
        <a href="https://example.com/careers#jobs">Careers</a>
        <a href="mailto:hello@example.com">Email</a>
        <a href="/about">Duplicate</a>
      </body>
    </html>
    """
    monkeypatch.setattr("llmkit.web.website._fetch_html", lambda url: html)

    links = fetch_website_links("https://example.com")

    assert links == ["https://example.com/about", "https://example.com/careers"]


def test_fetch_website_contents_with_local_html(monkeypatch) -> None:
    """Text extraction should ignore scripts and include source URL."""
    html = """
    <html>
      <head><style>.hidden {}</style></head>
      <body>
        <h1>Example Co</h1>
        <script>console.log("ignore")</script>
        <p>Builds useful industrial software.</p>
      </body>
    </html>
    """
    monkeypatch.setattr("llmkit.web.website._fetch_html", lambda url: html)

    contents = fetch_website_contents("https://example.com")

    assert "Source URL: https://example.com" in contents
    assert "Example Co" in contents
    assert "console.log" not in contents
