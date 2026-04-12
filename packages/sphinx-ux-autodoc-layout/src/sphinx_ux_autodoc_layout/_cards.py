"""Shared card-shell builders for non-``desc`` API entries.

Examples
--------
>>> from docutils import nodes
>>> entry = build_api_card_entry(
...     profile_class="gp-sphinx-api-profile--demo",
...     signature_children=(nodes.literal("", "demo"),),
... )
>>> entry["classes"][:2]
['gp-sphinx-api-entry', 'gp-sphinx-api-card-entry']
"""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_ux_autodoc_layout._css import API
from sphinx_ux_autodoc_layout._nodes import (
    api_permalink,
    build_api_component,
    build_api_inline_component,
)
from sphinx_ux_badges import SAB


def build_api_card_entry(
    *,
    profile_class: str,
    signature_children: t.Sequence[nodes.Node],
    content_children: t.Sequence[nodes.Node] = (),
    badge_group: nodes.Node | None = None,
    permalink: api_permalink | None = None,
    entry_classes: tuple[str, ...] = (),
    signature_classes: tuple[str, ...] = (),
    content_classes: tuple[str, ...] = (),
) -> nodes.Element:
    """Build a shared ``gp-sphinx-api-*`` card entry for non-``desc`` consumers.

    Parameters
    ----------
    profile_class : str
        Stable profile class such as ``"gp-sphinx-api-profile--fastmcp-tool"``.
    signature_children : Sequence[nodes.Node]
        Children placed inside the ``gp-sphinx-api-signature`` wrapper.
    content_children : Sequence[nodes.Node]
        Children appended to ``gp-sphinx-api-content``.
    badge_group : nodes.Node | None
        Shared badge group rendered inside ``gp-sphinx-api-badge-container``.
    permalink : api_permalink | None
        Explicit header permalink placed in ``gp-sphinx-api-layout-left``.
    entry_classes : tuple[str, ...]
        Extra CSS classes for the outer ``gp-sphinx-api-entry`` wrapper.
    signature_classes : tuple[str, ...]
        Extra classes for the ``gp-sphinx-api-signature`` wrapper.
    content_classes : tuple[str, ...]
        Extra classes for the ``gp-sphinx-api-content`` wrapper.

    Returns
    -------
    nodes.Element
        Shared card entry tree using the stable ``gp-sphinx-api-*`` contract.
    """
    entry = build_api_component(
        API.ENTRY,
        classes=(API.CARD_ENTRY, profile_class, *entry_classes),
    )
    header = build_api_component(API.HEADER)
    layout = build_api_component(API.LAYOUT)
    left = build_api_component(API.LAYOUT_LEFT)
    signature = build_api_component(
        API.SIGNATURE,
        classes=signature_classes,
    )
    for child in signature_children:
        signature += child
    left += signature
    if permalink is not None:
        left += permalink

    right = build_api_component(API.LAYOUT_RIGHT, classes=(SAB.TOOLBAR,))
    if badge_group is not None:
        badge_container = build_api_inline_component(API.BADGE_CONTAINER)
        badge_container += badge_group
        right += badge_container

    layout += left
    layout += right
    header += layout
    entry += header

    content = build_api_component(API.CONTENT, classes=content_classes)
    for child in content_children:
        content += child
    entry += content
    return entry
