"""Integration tests for llms.txt generation."""

from __future__ import annotations

import typing as t

import pytest

if t.TYPE_CHECKING:
    from tests.ext.llms.conftest import LlmsBuildResult

pytestmark = pytest.mark.integration


class LlmsTxtCase(t.NamedTuple):
    """Test case for llms.txt content assertions."""

    test_id: str
    expected_substring: str


_CASES: list[LlmsTxtCase] = [
    LlmsTxtCase(
        test_id="h1-is-project-name",
        expected_substring="# llms-test",
    ),
    LlmsTxtCase(
        test_id="blockquote-summary",
        expected_substring="> A test project for LLM documentation outputs.",
    ),
    LlmsTxtCase(
        test_id="guide-section-heading",
        expected_substring="## Guide",
    ),
    LlmsTxtCase(
        test_id="reference-section-heading",
        expected_substring="## Reference",
    ),
    LlmsTxtCase(
        test_id="quickstart-link",
        expected_substring="[Quickstart](https://example.org/quickstart.html)",
    ),
    LlmsTxtCase(
        test_id="api-link",
        expected_substring="[API Reference](https://example.org/api.html)",
    ),
]


@pytest.mark.parametrize(
    list(LlmsTxtCase._fields),
    _CASES,
    ids=[c.test_id for c in _CASES],
)
def test_llms_txt_content(
    test_id: str,
    expected_substring: str,
    llms_txt_content: str,
) -> None:
    """llms.txt contains the expected structure."""
    assert expected_substring in llms_txt_content


def test_llms_txt_file_exists(llms_build: LlmsBuildResult) -> None:
    """llms.txt is written to the output directory."""
    assert llms_build.llms_txt_path.exists()
