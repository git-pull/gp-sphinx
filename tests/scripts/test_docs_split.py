"""Tests for ``scripts/docs_split.py`` (one-shot migration helper)."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import textwrap
import typing as t

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SCRIPT_PATH = REPO_ROOT / "scripts" / "docs_split.py"


def _load_docs_split() -> t.Any:
    """Import ``scripts/docs_split.py`` as a module under a stable name."""
    spec = importlib.util.spec_from_file_location("scripts_docs_split", _SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["scripts_docs_split"] = mod
    spec.loader.exec_module(mod)
    return mod


docs_split = _load_docs_split()


class _ClassifyCase(t.NamedTuple):
    """Fixture row: H2 heading text -> expected target bucket."""

    test_id: str
    heading: str
    expected: str | None


_CLASSIFY_CASES: list[_ClassifyCase] = [
    _ClassifyCase("live_demos_examples", "Live demos", "examples"),
    _ClassifyCase("tool_cards_examples", "Tool cards", "examples"),
    _ClassifyCase("config_values_reference", "Configuration values", "reference"),
    _ClassifyCase("directives_reference", "Directives", "reference"),
    _ClassifyCase("colour_palette_reference", "Colour palette", "reference"),
    _ClassifyCase("color_palette_reference", "Color palette", "reference"),
    _ClassifyCase("custom_properties_reference", "CSS custom properties", "reference"),
    _ClassifyCase(
        "downstream_extensions_explanation",
        "Downstream extensions",
        "explanation",
    ),
    _ClassifyCase("downstream_conf_tutorial", "Downstream conf.py", "tutorial"),
    _ClassifyCase("usage_examples_tutorial", "Working usage examples", "tutorial"),
    _ClassifyCase("package_reference_deleted", "Package reference", None),
    _ClassifyCase("any_reference_section_to_reference", "API reference", "reference"),
    _ClassifyCase("unmatched_falls_to_howto", "fastmcp_server_module", "how-to"),
]


@pytest.mark.parametrize(
    list(_ClassifyCase._fields),
    _CLASSIFY_CASES,
    ids=[case.test_id for case in _CLASSIFY_CASES],
)
def test_classify_heading(test_id: str, heading: str, expected: str | None) -> None:
    """Heading text routes to the expected Diátaxis bucket."""
    assert docs_split.classify_heading(heading) == expected


def test_parse_h2_sections_drops_preamble_and_groups_by_heading() -> None:
    """Lines before the first ``## ...`` are discarded; bodies are captured."""
    text = textwrap.dedent("""
        # Title

        intro

        ## First

        body of first

        ## Second

        body of second
    """).lstrip()
    sections = docs_split.parse_h2_sections(text)
    assert [s.heading_text for s in sections] == ["First", "Second"]
    assert "body of first" in "\n".join(sections[0].body_lines)
    assert "body of second" in "\n".join(sections[1].body_lines)


def test_classify_flat_page_buckets_real_sections(tmp_path: pathlib.Path) -> None:
    """End-to-end: classify_flat_page returns expected bucket distribution."""
    flat = tmp_path / "demo-pkg.md"
    flat.write_text(
        textwrap.dedent("""
            # demo-pkg

            ## Live demos

            demo body

            ## Reference

            ref body

            ## Downstream extensions

            why body

            ## Package reference

            (auto-generated, deleted)
        """).lstrip(),
        encoding="utf-8",
    )
    outcome = docs_split.classify_flat_page(flat)
    assert outcome.package_name == "demo-pkg"
    assert sorted(outcome.sections_by_bucket.keys()) == [
        "examples",
        "explanation",
        "reference",
    ]
    assert outcome.deleted_headings == ["Package reference"]


def test_assemble_subpage_emits_anchor_title_and_section() -> None:
    """assemble_subpage produces the expected MyST shell."""
    sections = [docs_split.H2Section("Live demos", ["", "demo body", ""])]
    rendered = docs_split.assemble_subpage("foo", "examples", sections)
    assert rendered.startswith("(foo-examples)=")
    assert "# Examples" in rendered
    assert "## Live demos" in rendered
    assert "demo body" in rendered


def test_stub_markdown_includes_anchor_h1_and_directive() -> None:
    """The stub carries anchor + H1 (so Sphinx finds a page title) + directive."""
    rendered = docs_split.stub_markdown("sphinx-fonts")
    lines = [line for line in rendered.splitlines() if line]
    assert lines == [
        "(sphinx-fonts)=",
        "# sphinx-fonts",
        "```{package-landing} sphinx-fonts",
        "```",
    ]


def test_assert_no_filler_raises_on_banned_pattern() -> None:
    """Generated text containing a denylist token raises ValueError."""
    with pytest.raises(ValueError, match="banned filler"):
        docs_split.assert_no_filler("# Title\n\nTBD\n", source_label="foo/tutorial.md")


def test_assert_no_filler_passes_on_clean_text() -> None:
    """Real prose passes the denylist."""
    docs_split.assert_no_filler(
        "# Tutorial\n\nDocument your first tool.\n",
        source_label="foo/tutorial.md",
    )


def test_render_report_shows_bucket_distribution_and_deletions() -> None:
    """Report mode summarizes which sections go where."""
    outcome = docs_split._SplitOutcome(
        sections_by_bucket={
            "examples": [docs_split.H2Section("Live demos", [])],
            "reference": [docs_split.H2Section("Configuration values", [])],
        },
        deleted_headings=["Package reference"],
        package_name="demo-pkg",
    )
    report = docs_split.render_report(outcome)
    assert "demo-pkg" in report
    assert "-> examples.md" in report
    assert "-> reference.md" in report
    assert "Deleted" in report
    assert "Package reference" in report
