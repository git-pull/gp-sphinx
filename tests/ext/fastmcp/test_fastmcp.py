"""Tests for sphinx_autodoc_fastmcp."""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_autodoc_badges import BadgeNode
from sphinx_autodoc_fastmcp._badges import build_safety_badge, build_tool_badge_group
from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_autodoc_fastmcp._parsing import (
    extract_params,
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
    assert "sab-badge-group" in group["classes"]
    badges = list(group.findall(BadgeNode))
    assert len(badges) == 2
    assert "tool" in badges[-1].astext()


def test_safety_badge_is_badge_node() -> None:
    """Safety badge is a BadgeNode (shared package)."""
    b = build_safety_badge("mutating")
    assert isinstance(b, BadgeNode)
    assert isinstance(b, nodes.inline)
    assert b.astext() == "mutating"


def test_safety_badge_has_classes() -> None:
    """Safety badge has sab-badge + smf safety classes."""
    b = build_safety_badge("readonly")
    assert "sab-badge" in b["classes"]
    assert "smf-safety-readonly" in b["classes"]


def test_safety_badge_icon_only() -> None:
    """Icon-only safety badge has sab-icon-only class and empty text."""
    b = build_safety_badge("readonly", icon_only=True)
    assert "sab-icon-only" in b["classes"]
    assert b.astext() == ""


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


def test_extract_params_uses_shared_literal_collapse() -> None:
    """FastMCP parameter extraction uses the shared literal normalization."""

    def list_sessions(
        status: t.Literal["open", "closed"],
        limit: int | None = None,
    ) -> str:
        return "[]"

    params = extract_params(list_sessions)

    assert [(param.name, param.type_str) for param in params] == [
        ("status", "'open', 'closed'"),
        ("limit", "int"),
    ]


def test_make_table_minimal() -> None:
    """make_table builds a table node."""
    t = make_table(["A"], [["x"]])
    assert isinstance(t, nodes.table)
