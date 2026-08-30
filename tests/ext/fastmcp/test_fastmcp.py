"""Tests for sphinx_autodoc_fastmcp."""

from __future__ import annotations

import logging
import sys
import types
import typing as t

import pytest
from docutils import nodes

from sphinx_autodoc_fastmcp._badges import build_axis_badge, build_tool_badge_group
from sphinx_autodoc_fastmcp._collector import _resolve_server_instance
from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_autodoc_fastmcp._parsing import (
    extract_params,
    first_paragraph,
    make_table,
    parse_numpy_params,
)
from sphinx_autodoc_fastmcp._roles import _tool_ref_placeholder
from sphinx_ux_badges import BadgeNode


def test_css_prefix() -> None:
    """CSS prefix is gp-sphinx-fastmcp."""
    assert _CSS.PREFIX == "gp-sphinx-fastmcp"


def test_badge_group_contains_tool_type() -> None:
    """Tool badge group renders the matched axes, then the type badge."""
    group = build_tool_badge_group({"risk": "readonly"})
    assert "gp-sphinx-badge-group" in group["classes"]
    badges = list(group.findall(BadgeNode))
    assert len(badges) == 2
    assert "tool" in badges[-1].astext()


def test_axis_badge_is_badge_node() -> None:
    """Safety badge is a BadgeNode (shared package)."""
    b = build_axis_badge("risk", "mutating")
    assert isinstance(b, BadgeNode)
    assert isinstance(b, nodes.inline)
    assert b.astext() == "mutating"


def test_axis_badge_has_axis_and_term_classes() -> None:
    """The badge names both its axis and its term, so CSS can target either."""
    b = build_axis_badge("risk", "readonly")
    assert "gp-sphinx-badge" in b["classes"]
    assert "gp-sphinx-fastmcp__axis-risk" in b["classes"]
    assert "gp-sphinx-fastmcp__risk-readonly" in b["classes"]


def test_axis_badge_icon_only() -> None:
    """Icon-only badge has the icon-only class and empty text."""
    b = build_axis_badge("risk", "readonly", icon_only=True)
    assert "gp-sphinx-badge--icon-only" in b["classes"]
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


def test_resolve_server_invokes_register_all_even_when_components_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hook fires regardless of pre-registered components.

    Servers may register some components at import time (decorators) while
    leaving others to an explicit ``register_all()`` — gating on
    ``_components`` being empty would silently drop the deferred ones.
    """
    calls: list[str] = []

    provider = types.SimpleNamespace(_components={"existing": object()})
    server = types.SimpleNamespace(local_provider=provider)

    fake_module = types.ModuleType("fake_fastmcp_server")
    fake_module.mcp = server  # type: ignore[attr-defined]
    fake_module.register_all = lambda: calls.append("register_all")  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "fake_fastmcp_server", fake_module)

    resolved = _resolve_server_instance("fake_fastmcp_server:mcp")

    assert resolved is server
    assert calls == ["register_all"]


def test_resolve_server_returns_none_when_attr_is_not_fastmcp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configured attr that is not a FastMCP instance resolves to ``None``.

    Returning the bare object would cause ``_iter_components`` to silently
    yield ``()`` and produce empty docs without any diagnostic.
    """
    calls: list[str] = []

    bare_obj = types.SimpleNamespace()  # no local_provider

    fake_module = types.ModuleType("fake_fastmcp_bare")
    fake_module.mcp = bare_obj  # type: ignore[attr-defined]
    fake_module.register_all = lambda: calls.append("register_all")  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "fake_fastmcp_bare", fake_module)

    resolved = _resolve_server_instance("fake_fastmcp_bare:mcp")

    assert resolved is None
    assert calls == []


def test_resolve_server_warns_when_attr_is_not_fastmcp(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The not-a-FastMCP path emits a WARNING-level diagnostic via caplog.records."""
    bare_obj = types.SimpleNamespace()
    fake_module = types.ModuleType("fake_fastmcp_bare2")
    fake_module.mcp = bare_obj  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fake_fastmcp_bare2", fake_module)

    with caplog.at_level(logging.WARNING, logger="sphinx_autodoc_fastmcp"):
        _resolve_server_instance("fake_fastmcp_bare2:mcp")

    matched = [
        r
        for r in caplog.records
        if r.name == "sphinx_autodoc_fastmcp._collector"
        and "local_provider" in r.getMessage()
    ]
    assert len(matched) == 1
    assert matched[0].levelno == logging.WARNING


def test_resolve_server_returns_none_when_factory_yields_non_fastmcp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A factory callable returning a non-FastMCP object resolves to ``None``."""
    fake_module = types.ModuleType("fake_fastmcp_factory")
    fake_module.mcp = lambda: types.SimpleNamespace()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fake_fastmcp_factory", fake_module)

    resolved = _resolve_server_instance("fake_fastmcp_factory:mcp")

    assert resolved is None


def test_no_axes_are_assumed_until_a_project_declares_them() -> None:
    """A default vocabulary would badge one project's tools with another's words."""
    from sphinx_autodoc_fastmcp._models import coerce_axes, resolve_axes

    assert coerce_axes(()) == ()
    assert resolve_axes((), tags={"anything"}) == {}


def test_precedence_follows_declaration_order() -> None:
    """A tool carrying several of an axis's terms takes the first declared."""
    from sphinx_autodoc_fastmcp._models import coerce_axes, resolve_axes

    axes = coerce_axes(
        ({"name": "cap", "terms": ("teardown", "execute", "manage", "inspect")},)
    )

    assert resolve_axes(axes, tags={"inspect", "teardown"}) == {"cap": "teardown"}
    assert resolve_axes(axes, tags={"manage", "inspect"}) == {"cap": "manage"}


def test_an_unrecognized_tag_takes_no_term() -> None:
    """A tool outside the vocabulary must not be reported as inside it."""
    from sphinx_autodoc_fastmcp._models import coerce_axes, resolve_axes

    axes = coerce_axes(({"name": "cap", "terms": ("inspect", "execute")},))

    assert resolve_axes(axes, tags={"mystery"}) == {}
    assert resolve_axes(axes, tags=set()) == {}


def test_two_axes_classify_one_tool_independently() -> None:
    """The point of axes: risk and topic can disagree without one winning.

    A single vocabulary forces a read-only lifecycle tool to be badged
    either by its risk or by its topic, never both.
    """
    from sphinx_autodoc_fastmcp._models import coerce_axes, resolve_axes

    axes = coerce_axes(
        (
            {"name": "risk", "terms": ("mutating", "readonly")},
            {"name": "topic", "terms": ("lifecycle", "metrics")},
        )
    )

    assert resolve_axes(axes, tags={"readonly", "lifecycle"}) == {
        "risk": "readonly",
        "topic": "lifecycle",
    }
    assert resolve_axes(axes, tags={"mutating", "lifecycle"}) == {
        "risk": "mutating",
        "topic": "lifecycle",
    }


def test_an_axis_can_read_its_term_from_mcp_hints() -> None:
    """MCP's own annotations classify a tool without any project config."""
    from sphinx_autodoc_fastmcp._models import DEFAULT_AXES, resolve_axes

    assert resolve_axes(DEFAULT_AXES, annotations={"readOnlyHint": True}) == {
        "risk": "readonly"
    }
    assert resolve_axes(
        DEFAULT_AXES, annotations={"readOnlyHint": False, "destructiveHint": True}
    ) == {"risk": "destructive"}
    assert resolve_axes(DEFAULT_AXES, annotations={}) == {}


def test_an_axis_can_read_its_term_from_tool_meta() -> None:
    """``meta`` is MCP's own extension point, so an axis can key off it."""
    from sphinx_autodoc_fastmcp._models import coerce_axes, resolve_axes

    axes = coerce_axes(({"name": "tier", "source": "meta:tier"},))

    assert resolve_axes(axes, meta={"tier": "gold"}) == {"tier": "gold"}
    assert resolve_axes(axes, meta={}) == {}


def test_a_declared_term_supplies_the_badge_tooltip_icon_and_tone() -> None:
    """Presentation is per term, so a project restyles without touching CSS."""
    from sphinx_autodoc_fastmcp._badges import build_axis_badge, use_axes
    from sphinx_autodoc_fastmcp._models import coerce_axes

    use_axes(
        coerce_axes(
            (
                {
                    "name": "risk",
                    "terms": (
                        {
                            "term": "teardown",
                            "tooltip": "Runs a command",
                            "icon": "X",
                            "tone": "red",
                        },
                    ),
                },
            )
        )
    )
    try:
        badge = build_axis_badge("risk", "teardown")
        assert badge["badge_tooltip"] == "Runs a command"
        assert "gp-sphinx-fastmcp__toolset--tone-red" in badge["classes"]
        # An undeclared term stays visible and claims nothing.
        mystery = build_axis_badge("risk", "mystery")
        assert mystery["badge_tooltip"] == "Risk: mystery"
        assert "gp-sphinx-fastmcp__toolset--tone-slate" in mystery["classes"]
    finally:
        use_axes(None)


def test_a_term_without_a_name_is_skipped(caplog: pytest.LogCaptureFixture) -> None:
    """One typo in conf.py costs a badge, not the build."""
    from sphinx_autodoc_fastmcp._models import coerce_axes

    with caplog.at_level(logging.WARNING, logger="sphinx_autodoc_fastmcp._models"):
        axes = coerce_axes(
            ({"name": "risk", "terms": ({"label": "oops"}, {"term": "inspect"})},)
        )

    assert [t.term for t in axes[0].terms] == ["inspect"]
    assert "has no 'term'" in caplog.text


def test_an_axis_without_a_name_is_skipped(caplog: pytest.LogCaptureFixture) -> None:
    """An axis with no name has no CSS class and no way to be referenced."""
    from sphinx_autodoc_fastmcp._models import coerce_axes

    with caplog.at_level(logging.WARNING, logger="sphinx_autodoc_fastmcp._models"):
        axes = coerce_axes(({"terms": ("a",)}, {"name": "risk"}))

    assert [a.name for a in axes] == ["risk"]
    assert "has no 'name'" in caplog.text
