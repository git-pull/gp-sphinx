"""Integration tests for docs.json generation."""

from __future__ import annotations

import typing as t

import pytest

if t.TYPE_CHECKING:
    from tests.ext.llms.conftest import LlmsBuildResult

pytestmark = pytest.mark.integration


def test_docs_json_file_exists(llms_build: LlmsBuildResult) -> None:
    """docs.json is written to the output directory."""
    assert llms_build.docs_json_path.exists()


def test_docs_json_name(docs_json_data: dict[str, t.Any]) -> None:
    """docs.json name matches the project name."""
    assert docs_json_data["name"] == "llms-test"


def test_docs_json_url(docs_json_data: dict[str, t.Any]) -> None:
    """docs.json url is the site URL without trailing slash."""
    assert docs_json_data["url"] == "https://example.org"


def test_docs_json_agent_entrypoints(docs_json_data: dict[str, t.Any]) -> None:
    """docs.json agentEntrypoints has the expected keys."""
    ep = docs_json_data["agentEntrypoints"]
    assert ep["manifest"] == "/docs.json"
    assert ep["llms"] == "/llms.txt"
    assert ep["llmsFull"] == "/llms-full.txt"


def test_docs_json_pages_count(docs_json_data: dict[str, t.Any]) -> None:
    """docs.json pages array has an entry per document."""
    pages = docs_json_data["pages"]
    page_urls = {p["url"] for p in pages}
    assert "/quickstart.html" in page_urls
    assert "/api.html" in page_urls
    assert "/advanced.html" in page_urls
    assert "/index.html" in page_urls


class PageFieldCase(t.NamedTuple):
    """Test case for docs.json page field presence."""

    test_id: str
    field: str


_PAGE_FIELD_CASES: list[PageFieldCase] = [
    PageFieldCase(test_id="has-title", field="title"),
    PageFieldCase(test_id="has-description", field="description"),
    PageFieldCase(test_id="has-section", field="section"),
    PageFieldCase(test_id="has-url", field="url"),
    PageFieldCase(test_id="has-markdownUrl", field="markdownUrl"),
    PageFieldCase(test_id="has-headings", field="headings"),
]


@pytest.mark.parametrize(
    list(PageFieldCase._fields),
    _PAGE_FIELD_CASES,
    ids=[c.test_id for c in _PAGE_FIELD_CASES],
)
def test_docs_json_page_has_field(
    test_id: str,
    field: str,
    docs_json_data: dict[str, t.Any],
) -> None:
    """Every page in docs.json has the expected field."""
    for page in docs_json_data["pages"]:
        assert field in page, f"page {page.get('url', '?')} missing '{field}'"


def test_docs_json_quickstart_headings(
    docs_json_data: dict[str, t.Any],
) -> None:
    """Quickstart page has extracted headings."""
    pages = docs_json_data["pages"]
    qs = next(p for p in pages if p["url"] == "/quickstart.html")
    heading_texts = [h["text"] for h in qs["headings"]]
    assert "Quickstart" in heading_texts
    assert "Installation" in heading_texts
    assert "Usage" in heading_texts
