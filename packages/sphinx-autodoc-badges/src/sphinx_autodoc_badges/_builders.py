"""Badge builder helpers -- typed API for creating badge nodes.

Examples
--------
>>> b = build_badge("readonly", tooltip="Read-only", classes=["smf-safety-readonly"])
>>> b.astext()
'readonly'

>>> "sab-badge" in b["classes"]
True
"""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_autodoc_badges._nodes import BadgeNode


def build_badge(
    text: str,
    *,
    tooltip: str = "",
    icon: str = "",
    classes: t.Sequence[str] = (),
    style: str = "full",
    fill: str = "filled",
    size: str = "",
    tabindex: str = "0",
) -> BadgeNode:
    """Build a single badge node.

    Parameters
    ----------
    text : str
        Visible label.  Empty string for icon-only badges.
    tooltip : str
        Hover text and ``aria-label``.
    icon : str
        Emoji character for CSS ``::before``.
    classes : Sequence[str]
        Additional CSS classes (plugin prefix + color class).
    style : str
        Structural variant: ``"full"``, ``"icon-only"``, ``"inline-icon"``.
    fill : str
        Visual fill: ``"filled"`` (default) or ``"outline"``.
    size : str
        Optional size tier: ``"xs"``, ``"sm"``, ``"lg"``, or ``"xl"``.
        Empty string uses the default (no extra class).
    tabindex : str
        ``"0"`` for focusable, ``""`` to skip.

    Returns
    -------
    BadgeNode

    Examples
    --------
    >>> b = build_badge("async", tooltip="Asynchronous", classes=["gas-mod-async"])
    >>> b.astext()
    'async'

    >>> b = build_badge("", style="icon-only", classes=["smf-safety-readonly"])
    >>> "sab-icon-only" in b["classes"]
    True

    >>> b = build_badge("big", size="lg")
    >>> "sab-lg" in b["classes"]
    True
    """
    extra_classes = list(classes)
    if fill == "outline":
        extra_classes.append("sab-outline")
    return BadgeNode(
        text,
        badge_tooltip=tooltip,
        badge_icon=icon,
        badge_style=style,
        badge_size=size,
        tabindex=tabindex,
        classes=extra_classes,
    )


def build_badge_group(
    badges: t.Sequence[BadgeNode],
    *,
    classes: t.Sequence[str] = (),
) -> nodes.inline:
    """Wrap badges in a group container with inter-badge spacing.

    Parameters
    ----------
    badges : Sequence[BadgeNode]
        Badge nodes to group.
    classes : Sequence[str]
        Additional CSS classes on the group container.

    Returns
    -------
    nodes.inline

    Examples
    --------
    >>> from sphinx_autodoc_badges._nodes import BadgeNode
    >>> g = build_badge_group([BadgeNode("a"), BadgeNode("b")])
    >>> "sab-badge-group" in g["classes"]
    True
    """
    group = nodes.inline(classes=["sab-badge-group", *classes])
    for i, badge in enumerate(badges):
        if i > 0:
            group += nodes.Text(" ")
        group += badge
    return group


def build_toolbar(
    badge_group: nodes.inline,
    *,
    classes: t.Sequence[str] = (),
) -> nodes.inline:
    """Wrap a badge group in a toolbar (``margin-left: auto`` for flex titles).

    Parameters
    ----------
    badge_group : nodes.inline
        Badge group from :func:`build_badge_group`.
    classes : Sequence[str]
        Additional CSS classes on the toolbar.

    Returns
    -------
    nodes.inline

    Examples
    --------
    >>> from sphinx_autodoc_badges._nodes import BadgeNode
    >>> g = build_badge_group([BadgeNode("x")])
    >>> t = build_toolbar(g, classes=["smf-toolbar"])
    >>> "sab-toolbar" in t["classes"]
    True
    """
    toolbar = nodes.inline(classes=["sab-toolbar", *classes])
    toolbar += badge_group
    return toolbar
