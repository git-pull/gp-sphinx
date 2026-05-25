"""Integration tests for llms-full.txt generation."""

from __future__ import annotations

import typing as t

import pytest

if t.TYPE_CHECKING:
    from tests.ext.llms.conftest import LlmsBuildResult

pytestmark = pytest.mark.integration


class FullTxtCase(t.NamedTuple):
    """Test case for llms-full.txt content assertions."""

    test_id: str
    expected_substring: str


_CASES: list[FullTxtCase] = [
    FullTxtCase(
        test_id="contains-quickstart-title",
        expected_substring="# Quickstart",
    ),
    FullTxtCase(
        test_id="contains-api-title",
        expected_substring="# API Reference",
    ),
    FullTxtCase(
        test_id="contains-source-url",
        expected_substring="Source: https://example.org/",
    ),
    FullTxtCase(
        test_id="contains-separator",
        expected_substring="---",
    ),
    FullTxtCase(
        test_id="contains-quickstart-body",
        expected_substring="Get started with the project quickly.",
    ),
]


@pytest.mark.parametrize(
    list(FullTxtCase._fields),
    _CASES,
    ids=[c.test_id for c in _CASES],
)
def test_llms_full_txt_content(
    test_id: str,
    expected_substring: str,
    llms_full_content: str,
) -> None:
    """llms-full.txt contains the expected page content."""
    assert expected_substring in llms_full_content


def test_llms_full_txt_file_exists(llms_build: LlmsBuildResult) -> None:
    """llms-full.txt is written to the output directory."""
    assert llms_build.llms_full_path.exists()
