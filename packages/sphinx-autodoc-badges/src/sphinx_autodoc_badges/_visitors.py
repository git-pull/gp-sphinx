"""HTML5 visitors for BadgeNode."""

from __future__ import annotations

import typing as t

from sphinx.writers.html5 import HTML5Translator

if t.TYPE_CHECKING:
    from sphinx_autodoc_badges._nodes import BadgeNode


def visit_badge_html(self: HTML5Translator, node: BadgeNode) -> None:
    """Emit opening ``<span>`` with ARIA, tooltip, icon data attribute.

    Uses ``self.starttag()`` which auto-emits ``class="..."`` from
    ``node["classes"]``.

    Examples
    --------
    >>> from sphinx_autodoc_badges._nodes import BadgeNode
    >>> b = BadgeNode("ok", badge_tooltip="tip")
    >>> b["badge_tooltip"]
    'tip'
    """
    attrs: dict[str, str] = {}

    tooltip = node.get("badge_tooltip", "")
    if tooltip:
        attrs["title"] = tooltip
        attrs["aria-label"] = tooltip

    icon = node.get("badge_icon", "")
    if icon:
        attrs["data-icon"] = icon

    tabindex = node.get("tabindex", "")
    if tabindex:
        attrs["tabindex"] = tabindex

    self.body.append(self.starttag(node, "span", "", role="note", **attrs))  # type: ignore[arg-type]


def depart_badge_html(self: HTML5Translator, node: BadgeNode) -> None:
    """Close the ``<span>``."""
    self.body.append("</span>")
