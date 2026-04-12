"""Tests for sphinx_ux_badges."""

from __future__ import annotations

import pytest
from docutils import nodes

from sphinx_ux_badges import (
    BadgeNode,
    BadgeSpec,
    build_badge,
    build_badge_from_spec,
    build_badge_group,
    build_badge_group_from_specs,
    build_toolbar,
)
from sphinx_ux_badges._css import SAB


def test_badge_node_is_inline_subclass() -> None:
    """BadgeNode subclasses nodes.inline for MRO fallback."""
    assert issubclass(BadgeNode, nodes.inline)
    b = BadgeNode("test")
    assert isinstance(b, nodes.inline)


def test_badge_node_has_base_class() -> None:
    """BadgeNode always gets gp-sphinx-badge class."""
    b = BadgeNode("readonly")
    assert SAB.BADGE in b["classes"]


def test_badge_node_text() -> None:
    """BadgeNode contains text child."""
    b = BadgeNode("hello")
    assert b.astext() == "hello"


def test_badge_node_empty() -> None:
    """Empty badge for icon-only has no text children."""
    b = BadgeNode("")
    assert b.astext() == ""


def test_badge_node_tooltip() -> None:
    """Tooltip stored as badge_tooltip attribute."""
    b = BadgeNode("x", badge_tooltip="tip")
    assert b["badge_tooltip"] == "tip"


def test_badge_node_icon() -> None:
    """Icon stored as badge_icon attribute."""
    b = BadgeNode("x", badge_icon="\U0001f50d")
    assert b["badge_icon"] == "\U0001f50d"


def test_badge_node_style_icon_only() -> None:
    """Icon-only style adds gp-sphinx-badge--icon-only class."""
    b = BadgeNode("", badge_style="icon-only")
    assert SAB.ICON_ONLY in b["classes"]


def test_badge_node_style_inline_icon() -> None:
    """Inline-icon style adds gp-sphinx-badge--inline-icon class."""
    b = BadgeNode("", badge_style="inline-icon")
    assert SAB.INLINE_ICON in b["classes"]


def test_badge_node_tabindex() -> None:
    """Tabindex defaults to '0'."""
    b = BadgeNode("x")
    assert b["tabindex"] == "0"


def test_badge_node_extra_classes() -> None:
    """Extra classes are appended."""
    b = BadgeNode(
        "x", classes=["gp-sphinx-fastmcp__safety-readonly", "gp-sphinx-fastmcp__safety"]
    )
    assert "gp-sphinx-fastmcp__safety-readonly" in b["classes"]
    assert SAB.BADGE in b["classes"]


def test_build_badge_basic() -> None:
    """build_badge creates a BadgeNode with correct text."""
    b = build_badge("readonly", tooltip="Read-only")
    assert isinstance(b, BadgeNode)
    assert b.astext() == "readonly"
    assert b["badge_tooltip"] == "Read-only"


def test_build_badge_from_spec() -> None:
    """Typed badge specs render through the shared builder."""
    spec = BadgeSpec(
        "config",
        tooltip="Sphinx config value",
        classes=("sas-badge--type",),
    )
    badge = build_badge_from_spec(spec)

    assert isinstance(badge, BadgeNode)
    assert badge.astext() == "config"
    assert "sas-badge--type" in badge["classes"]


def test_build_badge_icon_only() -> None:
    """build_badge with icon-only style."""
    b = build_badge(
        "", style="icon-only", classes=["gp-sphinx-fastmcp__safety-readonly"]
    )
    assert SAB.ICON_ONLY in b["classes"]
    assert "gp-sphinx-fastmcp__safety-readonly" in b["classes"]
    assert b.astext() == ""


def test_build_badge_outline() -> None:
    """build_badge with outline fill adds gp-sphinx-badge--outline class."""
    b = build_badge(
        "function", fill="outline", classes=["gp-sphinx-badge--type-function"]
    )
    assert SAB.OUTLINE in b["classes"]
    assert "gp-sphinx-badge--type-function" in b["classes"]


def test_badge_node_size() -> None:
    """badge_size adds sab-{xs,sm,lg,xl} class."""
    assert SAB.LG in BadgeNode("x", badge_size="lg")["classes"]


def test_badge_node_invalid_size_raises() -> None:
    """Invalid badge_size raises ValueError."""
    with pytest.raises(ValueError, match="badge_size"):
        BadgeNode("x", badge_size="huge")


def test_build_badge_size() -> None:
    """build_badge size= forwards to BadgeNode."""
    b = build_badge("label", size="sm")
    assert SAB.SM in b["classes"]
    assert b["badge_size"] == "sm"


def test_build_badge_group() -> None:
    """build_badge_group wraps badges with spacing."""
    b1 = build_badge("a")
    b2 = build_badge("b")
    g = build_badge_group([b1, b2], classes=["gp-sphinx-fastmcp__badge-group"])
    assert SAB.BADGE_GROUP in g["classes"]
    assert "gp-sphinx-fastmcp__badge-group" in g["classes"]
    badges = list(g.findall(BadgeNode))
    assert len(badges) == 2


def test_build_badge_group_from_specs() -> None:
    """Typed badge groups keep the shared gp-sphinx-badge-group wrapper."""
    group = build_badge_group_from_specs(
        [
            BadgeSpec("config", classes=("gp-sphinx-api-style__badge--type",)),
            BadgeSpec(
                "env",
                classes=("gp-sphinx-api-style__badge--rebuild",),
                fill="outline",
            ),
        ],
        classes=["gp-sphinx-api-style__badge-group"],
    )

    assert SAB.BADGE_GROUP in group["classes"]
    assert "gp-sphinx-api-style__badge-group" in group["classes"]
    assert [badge.astext() for badge in group.findall(BadgeNode)] == ["config", "env"]


def test_build_toolbar() -> None:
    """build_toolbar wraps a group in a toolbar container."""
    g = build_badge_group([build_badge("x")])
    t = build_toolbar(g, classes=["gp-sphinx-fastmcp__toolbar"])
    assert SAB.TOOLBAR in t["classes"]
    assert "gp-sphinx-fastmcp__toolbar" in t["classes"]


def test_badge_inside_reference() -> None:
    """BadgeNode can be nested inside a reference node."""
    ref = nodes.reference("", "", internal=True, refuri="#test")
    badge = build_badge("readonly", classes=["gp-sphinx-fastmcp__safety-readonly"])
    ref += badge
    found = list(ref.findall(BadgeNode))
    assert len(found) == 1


def test_badge_inside_literal() -> None:
    """BadgeNode can be nested inside a literal (code chip)."""
    code = nodes.literal("", "")
    badge = build_badge(
        "", style="inline-icon", classes=["gp-sphinx-fastmcp__safety-readonly"]
    )
    code += badge
    code += nodes.Text("capture_pane")
    found = list(code.findall(BadgeNode))
    assert len(found) == 1


def test_badge_next_to_literal_in_reference() -> None:
    """Icon-only badge + literal side by side inside a reference."""
    ref = nodes.reference("", "", internal=True, refuri="#test")
    badge = build_badge(
        "", style="icon-only", classes=["gp-sphinx-fastmcp__safety-readonly"]
    )
    ref += badge
    ref += nodes.literal("", "capture_pane")
    assert len(list(ref.findall(BadgeNode))) == 1
    assert len(list(ref.findall(nodes.literal))) == 1


def test_css_constants() -> None:
    """CSS constants use the gp-sphinx-badge namespace."""
    assert SAB.PREFIX == "gp-sphinx-badge"
    assert SAB.BADGE == "gp-sphinx-badge"
    assert SAB.ICON_ONLY == "gp-sphinx-badge--icon-only"
    assert SAB.XXS == "gp-sphinx-badge--size-xxs"
    assert SAB.XS == "gp-sphinx-badge--size-xs"
    assert SAB.SM == "gp-sphinx-badge--size-sm"
    assert SAB.MD == "gp-sphinx-badge--size-md"
    assert SAB.LG == "gp-sphinx-badge--size-lg"
    assert SAB.XL == "gp-sphinx-badge--size-xl"
