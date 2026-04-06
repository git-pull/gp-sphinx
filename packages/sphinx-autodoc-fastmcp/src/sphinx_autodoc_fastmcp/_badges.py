"""Badge nodes and HTML visitors for sphinx_autodoc_fastmcp."""

from __future__ import annotations

import typing as t

from docutils import nodes
from sphinx.writers.html5 import HTML5Translator

from sphinx_autodoc_fastmcp._css import _CSS

_SAFETY_LABELS = ("readonly", "mutating", "destructive")

_SAFETY_TOOLTIPS: dict[str, str] = {
    "readonly": "Read-only — does not modify external state",
    "mutating": "Mutating — creates or modifies objects",
    "destructive": "Destructive — may remove data; not reversible",
}

_TYPE_TOOLTIP = "MCP tool"


def build_safety_badge(
    safety: str,
    *,
    icon_only: bool = False,
) -> nodes.abbreviation:
    """Build a single safety tier badge as an ``abbreviation`` node.

    Parameters
    ----------
    safety : str
        One of ``readonly``, ``mutating``, ``destructive``.
    icon_only : bool
        When True, use a narrow non-breaking space for icon-only layouts.

    Returns
    -------
    nodes.abbreviation

    Examples
    --------
    >>> b = build_safety_badge("readonly")
    >>> b.astext()
    'readonly'
    """
    label = safety if safety in _SAFETY_LABELS else safety
    text = "\u00a0" if icon_only else label
    classes = [_CSS.BADGE, _CSS.BADGE_SAFETY]
    if safety in _SAFETY_LABELS:
        classes.append(_CSS.safety_class(safety))
    if icon_only:
        classes.append(f"{_CSS.PREFIX}-badge--icon-only")
    abbr = nodes.abbreviation(
        text,
        text,
        explanation=_SAFETY_TOOLTIPS.get(safety, f"Safety: {safety}"),
        classes=classes,
    )
    abbr["tabindex"] = "0"
    return abbr


def build_type_tool_badge() -> nodes.abbreviation:
    """Rightmost type badge labeling the entry as an MCP tool."""
    abbr = nodes.abbreviation(
        "tool",
        "tool",
        explanation=_TYPE_TOOLTIP,
        classes=[_CSS.BADGE, _CSS.BADGE_TYPE, _CSS.TYPE_TOOL],
    )
    abbr["tabindex"] = "0"
    return abbr


def build_tool_badge_group(safety: str) -> nodes.inline:
    """Badge group for a tool signature: safety tier + type ``tool``.

    Parameters
    ----------
    safety : str
        Safety tier name.

    Returns
    -------
    nodes.inline
        Container with class ``smf-badge-group``.

    Examples
    --------
    >>> g = build_tool_badge_group("readonly")
    >>> _CSS.BADGE_GROUP in g["classes"]
    True
    """
    group = nodes.inline(classes=[_CSS.BADGE_GROUP])
    safety_badge = build_safety_badge(safety)
    type_badge = build_type_tool_badge()
    group += safety_badge
    group += nodes.Text(" ")
    group += type_badge
    return group


def build_toolbar(safety: str) -> nodes.inline:
    """Toolbar container (signature right side): badge group only."""
    toolbar = nodes.inline(classes=[_CSS.TOOLBAR])
    toolbar += build_tool_badge_group(safety)
    return toolbar


def visit_abbreviation_html(
    self: HTML5Translator,
    node: nodes.abbreviation,
) -> None:
    """Emit ``<abbr>`` with ``tabindex`` when present (keyboard tooltips)."""
    attrs: dict[str, t.Any] = {}
    if node.get("explanation"):
        attrs["title"] = node["explanation"]
    if node.get("tabindex"):
        attrs["tabindex"] = node["tabindex"]
    self.body.append(self.starttag(node, "abbr", "", **attrs))


def depart_abbreviation_html(
    self: HTML5Translator,
    node: nodes.abbreviation,
) -> None:
    """Close the ``<abbr>`` tag."""
    self.body.append("</abbr>")
