"""Tests for sphinx_autodoc_fastmcp."""

from __future__ import annotations

from docutils import nodes

from sphinx_autodoc_fastmcp._badges import build_safety_badge, build_tool_badge_group
from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_autodoc_fastmcp._parsing import (
    first_paragraph,
    make_table,
    parse_numpy_params,
)
from sphinx_autodoc_fastmcp._roles import _tool_ref_placeholder


def test_css_prefix() -> None:
    """CSS prefix is smf."""
    assert _CSS.PREFIX == "smf"


def test_badge_group_contains_tool_type() -> None:
    """Tool badge group includes safety + type badge."""
    group = build_tool_badge_group("readonly")
    assert _CSS.BADGE_GROUP in group["classes"]
    abbrs = list(group.findall(nodes.abbreviation))
    assert len(abbrs) == 2
    assert "tool" in abbrs[-1].astext()


def test_safety_badge_abbreviation() -> None:
    """Safety badge is an abbreviation node."""
    b = build_safety_badge("mutating")
    assert isinstance(b, nodes.abbreviation)
    assert b.astext() == "mutating"


def test_tool_placeholder_node() -> None:
    """Placeholder stores hyphenated ref target."""
    n = _tool_ref_placeholder("", reftarget="list-sessions", show_badge=True)
    assert n["reftarget"] == "list-sessions"


def test_parse_numpy_empty() -> None:
    """Empty docstring yields no params."""
    assert parse_numpy_params("") == {}


def test_first_paragraph() -> None:
    """First paragraph is extracted."""
    assert first_paragraph("a\n\nb") == "a"


def test_make_table_minimal() -> None:
    """make_table builds a table node."""
    t = make_table(["A"], [["x"]])
    assert isinstance(t, nodes.table)
