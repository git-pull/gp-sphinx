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


def visit_badge_json(self: t.Any, node: BadgeNode) -> None:
    """Emit a Pydantic-shaped ``BadgeNode`` dict into the parent's children list.

    The visitor is registered with ``app.add_node(BadgeNode,
    json=(visit_badge_json, depart_badge_json))`` so ``gp-sphinx-astro-
    builder``'s :class:`DocTreeJSONTranslator` picks it up automatically
    via Sphinx's ``MethodType`` binding inside
    :meth:`SphinxComponentRegistry.create_translator`.

    The translator's ``append_node`` public hook is the contract — it
    handles "current frame has no ``children`` slot" gracefully so a
    badge inside an unhandled frame is dropped cleanly rather than
    crashing the build.

    Raises
    ------
    docutils.nodes.SkipNode
        Always: the badge text is captured via :meth:`docutils.nodes.
        Element.astext` on visit, so traversing the inner ``Text``
        child would double-count.
    """
    from docutils import nodes

    style = node.get("badge_style", "full") or "full"
    payload: dict[str, t.Any] = {
        "type": "badge",
        "text": node.astext(),
        "tooltip": node.get("badge_tooltip") or None,
        "icon": node.get("badge_icon") or None,
        "size": node.get("badge_size") or None,
        "style": style,
    }
    if hasattr(self, "append_node"):
        self.append_node(payload)
    raise nodes.SkipNode


def depart_badge_json(self: t.Any, node: BadgeNode) -> None:
    """No-op companion for :func:`visit_badge_json`.

    ``visit_badge_json`` raises :class:`docutils.nodes.SkipNode`, which
    causes docutils to skip the depart call — but we register the
    function anyway so ``app.add_node(..., json=(visit, depart))``
    accepts a non-``None`` depart pair.
    """
