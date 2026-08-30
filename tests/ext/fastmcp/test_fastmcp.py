"""Tests for sphinx_autodoc_fastmcp."""

from __future__ import annotations

import logging
import sys
import types
import typing as t

import pytest
from docutils import nodes

from sphinx_autodoc_fastmcp._badges import build_tool_badge_group, build_toolset_badge
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


def test_toolset_badge_is_badge_node() -> None:
    """Safety badge is a BadgeNode (shared package)."""
    b = build_toolset_badge("mutating")
    assert isinstance(b, BadgeNode)
    assert isinstance(b, nodes.inline)
    assert b.astext() == "mutating"


def test_toolset_badge_has_classes() -> None:
    """Safety badge has gp-sphinx-badge + smf safety classes."""
    b = build_toolset_badge("readonly")
    assert "gp-sphinx-badge" in b["classes"]
    assert "gp-sphinx-fastmcp__toolset-readonly" in b["classes"]


def test_toolset_badge_icon_only() -> None:
    """Icon-only safety badge has gp-sphinx-badge--icon-only class and empty text."""
    b = build_toolset_badge("readonly", icon_only=True)
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


def test_no_vocabulary_is_assumed_until_a_project_declares_one() -> None:
    """Shipping a default would badge one project's tools with another's words."""
    from sphinx_autodoc_fastmcp._models import DEFAULT_TOOLSETS, resolve_toolset

    assert DEFAULT_TOOLSETS == ()
    assert resolve_toolset({"anything"}, DEFAULT_TOOLSETS) == ""


def test_precedence_follows_declaration_order() -> None:
    """A tool carrying several tags takes the first one declared."""
    from sphinx_autodoc_fastmcp._models import coerce_toolsets, resolve_toolset

    tiers = coerce_toolsets(("teardown", "execute", "manage", "inspect"))

    assert resolve_toolset({"inspect", "teardown"}, tiers) == "teardown"
    assert resolve_toolset({"manage", "inspect"}, tiers) == "manage"


def test_an_unrecognized_tag_resolves_to_no_toolset() -> None:
    """A tool outside the vocabulary must not be reported as inside it."""
    from sphinx_autodoc_fastmcp._models import coerce_toolsets, resolve_toolset

    tiers = coerce_toolsets(("inspect", "execute"))

    assert resolve_toolset({"mystery"}, tiers) == ""
    assert resolve_toolset(set(), tiers) == ""


def test_a_project_can_supply_its_own_safety_vocabulary() -> None:
    """A renamed tag set resolves once the project declares it."""
    from sphinx_autodoc_fastmcp._models import coerce_toolsets, resolve_toolset

    tiers = coerce_toolsets(
        (
            {
                "tag": "teardown",
                "tooltip": "Removes tmux objects",
                "icon": "\U0001f4a3",
            },
            {"tag": "execute"},
            {"tag": "manage"},
            {"tag": "inspect"},
        )
    )

    assert resolve_toolset({"execute"}, tiers) == "execute"
    assert resolve_toolset({"inspect", "teardown"}, tiers) == "teardown"
    assert resolve_toolset({"readonly"}, tiers) == ""
    assert tiers[0].tooltip == "Removes tmux objects"


def test_a_tool_outside_the_vocabulary_gets_no_safety_badge() -> None:
    """No badge is honest; a badge naming a tier nobody assigned is not."""
    group = build_tool_badge_group("")

    assert group.astext() == "tool"


def test_configured_toolsets_supply_the_badge_tooltip_and_icon() -> None:
    """A project's own vocabulary reaches the rendered badge."""
    from sphinx_autodoc_fastmcp._badges import use_toolsets
    from sphinx_autodoc_fastmcp._models import coerce_toolsets

    use_toolsets(coerce_toolsets(({"tag": "execute", "tooltip": "Runs a command"},)))
    try:
        badge = build_toolset_badge("execute")
        assert badge["badge_tooltip"] == "Runs a command"
    finally:
        use_toolsets(None)

    assert build_toolset_badge("execute")["badge_tooltip"] == "Toolset: execute"


def test_a_toolset_badge_carries_its_declared_tone() -> None:
    """Colour comes from the project's declaration, not a guessed tag name.

    The stylesheet cannot ship a rule per tag, because it does not know
    what a project calls its toolsets. It ships tones instead, and the
    project maps onto them.
    """
    from sphinx_autodoc_fastmcp._badges import build_toolset_badge, use_toolsets
    from sphinx_autodoc_fastmcp._models import coerce_toolsets

    use_toolsets(coerce_toolsets(({"tag": "teardown", "tone": "red"},)))
    try:
        classes = build_toolset_badge("teardown")["classes"]
        assert "gp-sphinx-fastmcp__toolset--tone-red" in classes
        # An undeclared toolset still gets a visible badge, claiming nothing.
        assert (
            "gp-sphinx-fastmcp__toolset--tone-slate"
            in build_toolset_badge("mystery")["classes"]
        )
    finally:
        use_toolsets(None)


def test_a_toolset_entry_without_a_tag_is_skipped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """One typo in conf.py costs a badge, not the build."""
    from sphinx_autodoc_fastmcp._models import coerce_toolsets

    with caplog.at_level(logging.WARNING, logger="sphinx_autodoc_fastmcp._models"):
        toolsets = coerce_toolsets(({"name": "execute"}, {"tag": "inspect"}))

    assert [entry.tag for entry in toolsets] == ["inspect"]
    assert "has no 'tag'" in caplog.text


def test_an_unknown_tone_falls_back_to_slate(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The stylesheet has no rule for it, so the badge would render uncoloured."""
    from sphinx_autodoc_fastmcp._models import coerce_toolsets

    with caplog.at_level(logging.WARNING, logger="sphinx_autodoc_fastmcp._models"):
        (entry,) = coerce_toolsets(({"tag": "teardown", "tone": "grey"},))

    assert entry.tone == "slate"
    assert "unknown tone" in caplog.text
