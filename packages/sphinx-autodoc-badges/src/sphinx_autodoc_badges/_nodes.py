"""BadgeNode -- shared docutils node for inline badges.

Subclasses ``nodes.inline`` so that unregistered builders (text, LaTeX, man)
fall back to ``visit_inline`` via Sphinx's MRO-based dispatch.

Examples
--------
>>> node = BadgeNode("readonly", badge_tooltip="Read-only operation")
>>> node.astext()
'readonly'

>>> "sab-badge" in node["classes"]
True
"""

from __future__ import annotations

import typing as t

from docutils import nodes


class BadgeNode(nodes.inline):
    """Inline badge rendered as ``<span>`` with ARIA and icon support.

    Subclasses ``nodes.inline`` so unregistered builders (text, LaTeX, man)
    fall back to ``visit_inline`` via MRO dispatch in
    ``SphinxTranslator.dispatch_visit``.

    Examples
    --------
    >>> b = BadgeNode("hello", badge_tooltip="greeting")
    >>> b["badge_tooltip"]
    'greeting'

    >>> b.astext()
    'hello'
    """

    def __init__(
        self,
        text: str = "",
        *,
        badge_tooltip: str = "",
        badge_icon: str = "",
        badge_style: str = "full",
        tabindex: str = "0",
        classes: list[str] | None = None,
        **attributes: t.Any,
    ) -> None:
        children = [nodes.Text(text)] if text else []
        super().__init__("", *children, **attributes)
        self["classes"].append("sab-badge")
        if classes:
            self["classes"].extend(classes)
        if badge_tooltip:
            self["badge_tooltip"] = badge_tooltip
        if badge_icon:
            self["badge_icon"] = badge_icon
        if badge_style != "full":
            self["badge_style"] = badge_style
            self["classes"].append(f"sab-{badge_style}")
        if tabindex:
            self["tabindex"] = tabindex
