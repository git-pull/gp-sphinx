"""HTML5 visitors for BadgeNode."""

from __future__ import annotations

import typing as t

from sphinx.writers.html5 import HTML5Translator

if t.TYPE_CHECKING:
    from sphinx_ux_badges._nodes import BadgeNode


def visit_badge_html(self: HTML5Translator, node: BadgeNode) -> None:
    """Emit opening ``<span>`` with ARIA, tooltip, icon data attribute.

    The icon (``data-icon`` → ``::before`` CSS) sits on the outer badge span so
    that ``text-decoration`` on the inner ``.gp-sphinx-badge__label`` span cannot reach
    it.  This prevents emoji icons from inheriting any underline decoration,
    since CSS ``text-decoration`` cannot be suppressed on pseudo-elements from a
    parent element — but it can be scoped to a sibling span.

    Uses ``self.starttag()`` which auto-emits ``class="..."`` from
    ``node["classes"]``.

    Examples
    --------
    >>> from sphinx_ux_badges._nodes import BadgeNode
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
    # Inner label span: text-decoration is scoped here so icons (::before on
    # the outer span) are never underlined.
    self.body.append('<span class="gp-sphinx-badge__label">')


def depart_badge_html(self: HTML5Translator, node: BadgeNode) -> None:
    """Close the inner label ``<span>`` then the outer badge ``<span>``."""
    self.body.append("</span></span>")
