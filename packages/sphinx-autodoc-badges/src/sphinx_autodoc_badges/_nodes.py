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

>>> n2 = BadgeNode("sm", badge_size="sm")
>>> "sab-sm" in n2["classes"]
True
"""

from __future__ import annotations

import typing as t

from docutils import nodes

_BADGE_SIZES = frozenset({"xs", "sm", "lg", "xl"})


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
        badge_size: str = "",
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
        if badge_size:
            if badge_size not in _BADGE_SIZES:
                allowed = sorted(_BADGE_SIZES)
                msg = f"badge_size must be one of {allowed!r}, got {badge_size!r}"
                raise ValueError(msg)
            self["badge_size"] = badge_size
            self["classes"].append(f"sab-{badge_size}")
        if tabindex:
            self["tabindex"] = tabindex
