"""Shared card-shell builders for non-``desc`` API entries.

Examples
--------
>>> from docutils import nodes
>>> entry = build_api_card_entry(
...     profile_class="api-profile--demo",
...     signature_children=(nodes.literal("", "demo"),),
... )
>>> entry["classes"][:2]
['api-entry', 'api-card-entry']
"""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_ux_autodoc_layout._nodes import (
    api_permalink,
    build_api_component,
    build_api_inline_component,
)


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
    """Build a shared ``api-*`` card entry for non-``desc`` consumers.

    Parameters
    ----------
    profile_class : str
        Stable profile class such as ``"api-profile--fastmcp-tool"``.
    signature_children : Sequence[nodes.Node]
        Children placed inside the ``api-signature`` wrapper.
    content_children : Sequence[nodes.Node]
        Children appended to ``api-content``.
    badge_group : nodes.Node | None
        Shared badge group rendered inside ``api-badge-container``.
    permalink : api_permalink | None
        Explicit header permalink placed in ``api-layout-left``.
    entry_classes : tuple[str, ...]
        Extra CSS classes for the outer ``api-entry`` wrapper.
    signature_classes : tuple[str, ...]
        Extra classes for the ``api-signature`` wrapper.
    content_classes : tuple[str, ...]
        Extra classes for the ``api-content`` wrapper.

    Returns
    -------
    nodes.Element
        Shared card entry tree using the stable ``api-*`` contract.
    """
    entry = build_api_component(
        "api-entry",
        classes=("api-card-entry", profile_class, *entry_classes),
    )
    header = build_api_component("api-header")
    layout = build_api_component("api-layout")
    left = build_api_component("api-layout-left")
    signature = build_api_component(
        "api-signature",
        classes=signature_classes,
    )
    for child in signature_children:
        signature += child
    left += signature
    if permalink is not None:
        left += permalink

    right = build_api_component("api-layout-right", classes=("sab-toolbar",))
    if badge_group is not None:
        badge_container = build_api_inline_component("api-badge-container")
        badge_container += badge_group
        right += badge_container

    layout += left
    layout += right
    header += layout
    entry += header

    content = build_api_component("api-content", classes=content_classes)
    for child in content_children:
        content += child
    entry += content
    return entry
