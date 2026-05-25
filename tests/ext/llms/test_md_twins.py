"""Integration tests for per-page .md twin file generation."""

from __future__ import annotations

import typing as t

import pytest

if t.TYPE_CHECKING:
    from tests.ext.llms.conftest import LlmsBuildResult

pytestmark = pytest.mark.integration


class MdTwinCase(t.NamedTuple):
    """Test case for .md twin file existence."""

    test_id: str
    docname: str


_CASES: list[MdTwinCase] = [
    MdTwinCase(test_id="index", docname="index"),
    MdTwinCase(test_id="quickstart", docname="quickstart"),
    MdTwinCase(test_id="advanced", docname="advanced"),
    MdTwinCase(test_id="api", docname="api"),
]


@pytest.mark.parametrize(
    list(MdTwinCase._fields),
    _CASES,
    ids=[c.test_id for c in _CASES],
)
def test_md_twin_exists(
    test_id: str,
    docname: str,
    llms_build: LlmsBuildResult,
) -> None:
    """A .md twin file exists alongside each HTML page."""
    md_path = llms_build.result.outdir / f"{docname}.md"
    assert md_path.exists(), f"{docname}.md not found in build output"


def test_md_twin_content_matches_source(
    llms_build: LlmsBuildResult,
) -> None:
    """The .md twin content matches the original source file."""
    md_content = (llms_build.result.outdir / "quickstart.md").read_text(
        encoding="utf-8",
    )
    assert "Get started with the project quickly." in md_content
