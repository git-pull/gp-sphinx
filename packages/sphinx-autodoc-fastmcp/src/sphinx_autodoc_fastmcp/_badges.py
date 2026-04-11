"""Badge helpers for sphinx_autodoc_fastmcp (thin wrappers over shared API)."""

from __future__ import annotations

import typing as t

from docutils import nodes
from sphinx_autodoc_badges import (
    SAB,
    BadgeNode,
    BadgeSpec,
    build_badge,
    build_badge_group_from_specs,
    build_toolbar as _sab_build_toolbar,
)

from sphinx_autodoc_fastmcp._css import _CSS

_SAFETY_LABELS = ("readonly", "mutating", "destructive")

_SAFETY_TOOLTIPS: dict[str, str] = {
    "readonly": "Read-only \u2014 does not modify external state",
    "mutating": "Mutating \u2014 creates or modifies objects",
    "destructive": "Destructive \u2014 may remove data; not reversible",
}

_SAFETY_ICONS: dict[str, str] = {
    "readonly": "\U0001f50d",
    "mutating": "\u270f\ufe0f",
    "destructive": "\U0001f4a3",
}

_TYPE_TOOLTIP = "MCP tool"


def build_safety_badge(
    safety: str,
    *,
    icon_only: bool = False,
) -> BadgeNode:
    """Build a safety tier badge.

    Parameters
    ----------
    safety : str
        One of ``readonly``, ``mutating``, ``destructive``.
    icon_only : bool
        When True, create an icon-only badge (empty text, 16x16 colored box).

    Returns
    -------
    BadgeNode

    Examples
    --------
    >>> b = build_safety_badge("readonly")
    >>> b.astext()
    'readonly'
    """
    label = safety if safety in _SAFETY_LABELS else safety
    text = "" if icon_only else label
    style: t.Literal["full", "icon-only", "inline-icon"] = (
        "icon-only" if icon_only else "full"
    )
    classes = [SAB.DENSE, _CSS.BADGE_SAFETY, _CSS.safety_class(safety)]
    return build_badge(
        text,
        tooltip=_SAFETY_TOOLTIPS.get(safety, f"Safety: {safety}"),
        icon=_SAFETY_ICONS.get(safety, ""),
        classes=classes,
        style=style,
    )


def build_type_tool_badge() -> BadgeNode:
    """Rightmost type badge labeling the entry as an MCP tool.

    Examples
    --------
    >>> b = build_type_tool_badge()
    >>> b.astext()
    'tool'
    """
    return build_badge(
        "tool",
        tooltip=_TYPE_TOOLTIP,
        classes=[SAB.DENSE, SAB.BADGE_TYPE, _CSS.TYPE_TOOL],
    )


def build_tool_badge_group(safety: str) -> nodes.inline:
    """Badge group: safety tier + type ``tool``.

    Parameters
    ----------
    safety : str
        Safety tier name.

    Returns
    -------
    nodes.inline

    Examples
    --------
    >>> g = build_tool_badge_group("readonly")
    >>> "sab-badge-group" in g["classes"]
    True
    """
    return build_badge_group_from_specs(
        [
            BadgeSpec(
                safety if safety in _SAFETY_LABELS else safety,
                tooltip=_SAFETY_TOOLTIPS.get(safety, f"Safety: {safety}"),
                icon=_SAFETY_ICONS.get(safety, ""),
                classes=(SAB.DENSE, _CSS.BADGE_SAFETY, _CSS.safety_class(safety)),
            ),
            BadgeSpec(
                "tool",
                tooltip=_TYPE_TOOLTIP,
                classes=(SAB.DENSE, SAB.BADGE_TYPE, _CSS.TYPE_TOOL),
            ),
        ],
    )


def build_toolbar(safety: str) -> nodes.inline:
    """Toolbar on the title row (flex ``margin-left: auto``).

    Examples
    --------
    >>> t = build_toolbar("readonly")
    >>> "sab-toolbar" in t["classes"]
    True
    """
    return _sab_build_toolbar(build_tool_badge_group(safety))
