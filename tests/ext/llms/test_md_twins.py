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


_GENERATED_PAGES = ["genindex", "py-modindex", "search"]


@pytest.mark.parametrize("pagename", _GENERATED_PAGES)
def test_generated_pages_advertise_no_md_twin(
    pagename: str,
    llms_build: LlmsBuildResult,
) -> None:
    """A page Sphinx generates has no source, so it must not link a twin."""
    from sphinx_gp_llms._md_twins import has_md_twin

    app = llms_build.result.app
    assert not has_md_twin(app, pagename)
    assert not (llms_build.result.outdir / f"{pagename}.md").exists()


def test_the_twin_link_and_the_twin_writer_agree(
    llms_build: LlmsBuildResult,
) -> None:
    """Every page advertising a twin has one, and vice versa.

    The footer link is rendered from the template rather than resolved as a
    reference, so Sphinx never reports a twin link that points at nothing --
    not even under ``-W``. This invariant is what catches it instead.
    """
    from sphinx_gp_llms._md_twins import has_md_twin

    app = llms_build.result.app
    outdir = llms_build.result.outdir
    candidates = sorted(app.env.found_docs) + _GENERATED_PAGES

    advertised = {name for name in candidates if has_md_twin(app, name)}
    written = {name for name in candidates if (outdir / f"{name}.md").exists()}

    assert advertised == written


class TwinContextCase(t.NamedTuple):
    """Whether a pagename should be offered a Markdown twin link."""

    test_id: str
    pagename: str
    expects_link: bool


_CONTEXT_CASES: list[TwinContextCase] = [
    TwinContextCase(test_id="real-page", pagename="index", expects_link=True),
    TwinContextCase(test_id="genindex", pagename="genindex", expects_link=False),
    TwinContextCase(test_id="modindex", pagename="py-modindex", expects_link=False),
    TwinContextCase(test_id="search", pagename="search", expects_link=False),
]


@pytest.mark.parametrize(
    list(TwinContextCase._fields),
    _CONTEXT_CASES,
    ids=[c.test_id for c in _CONTEXT_CASES],
)
def test_only_a_page_with_a_twin_is_offered_the_link(
    test_id: str,
    pagename: str,
    expects_link: bool,
    llms_build: LlmsBuildResult,
) -> None:
    """The footer variable is set only when the twin was written."""
    from sphinx_gp_llms import _inject_llms_context

    context: dict[str, t.Any] = {}
    _inject_llms_context(llms_build.result.app, pagename, "page.html", context, None)

    assert ("llms_md_url" in context) is expects_link
