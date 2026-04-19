"""Tests for sphinx_autodoc_fastmcp."""

from __future__ import annotations

import logging
import sys
import types
import typing as t

import pytest
from docutils import nodes

from sphinx_autodoc_fastmcp._badges import build_safety_badge, build_tool_badge_group
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
    """Tool badge group includes safety + type badge."""
    group = build_tool_badge_group("readonly")
    assert "gp-sphinx-badge-group" in group["classes"]
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
    """Safety badge has gp-sphinx-badge + smf safety classes."""
    b = build_safety_badge("readonly")
    assert "gp-sphinx-badge" in b["classes"]
    assert "gp-sphinx-fastmcp__safety-readonly" in b["classes"]


def test_safety_badge_icon_only() -> None:
    """Icon-only safety badge has gp-sphinx-badge--icon-only class and empty text."""
    b = build_safety_badge("readonly", icon_only=True)
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
