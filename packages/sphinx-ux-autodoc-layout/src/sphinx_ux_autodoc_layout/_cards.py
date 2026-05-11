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
    api_component,
    api_permalink,
    build_api_component,
    build_api_inline_component,
)
from sphinx_ux_badges import SAB


def _clone_node(node: nodes.Node) -> nodes.Node:
    """Return an independent copy of *node* via docutils' own ``deepcopy``.

    Stdlib ``copy.deepcopy`` is unsafe for docutils nodes: ``Node`` does
    not override ``__deepcopy__``, so the default machinery follows
    ``.parent`` upward and clones every ancestor.  Docutils'
    ``Element.deepcopy`` walks only descendants — what we want when
    duplicating header content for the desktop and mobile variants.
    """
    if isinstance(node, nodes.Node):
        return node.deepcopy()
    return node


def _build_card_signature_column(
    signature_children: t.Sequence[nodes.Node],
    permalink: api_permalink | None,
    *,
    signature_classes: tuple[str, ...],
) -> tuple[api_component, api_permalink | None]:
    """Build a fresh signature column (signature + permalink) for one variant."""
    signature = build_api_component(API.SIGNATURE, classes=signature_classes)
    for child in signature_children:
        signature += _clone_node(child)
    cloned_permalink = permalink.deepcopy() if permalink is not None else None
    return signature, cloned_permalink


def _build_card_toolbar_column(
    badge_group: nodes.Node | None,
    *,
    name: str,
) -> api_component:
    """Build a fresh toolbar column for one variant."""
    column = build_api_component(name, classes=(SAB.TOOLBAR,))
    if badge_group is not None:
        badge_container = build_api_inline_component(API.BADGE_CONTAINER)
        badge_container += _clone_node(badge_group)
        column += badge_container
    return column


def _build_card_layout_variant(
    *,
    variant: str,
    signature_children: t.Sequence[nodes.Node],
    permalink: api_permalink | None,
    badge_group: nodes.Node | None,
    signature_classes: tuple[str, ...],
) -> api_component:
    """Build a complete card layout variant (desktop or mobile)."""
    layout = build_api_component(
        API.LAYOUT,
        classes=(API.layout_variant(variant),),
    )
    signature, cloned_permalink = _build_card_signature_column(
        signature_children,
        permalink,
        signature_classes=signature_classes,
    )

    if variant == "desktop":
        left = build_api_component(API.LAYOUT_LEFT)
        left += signature
        if cloned_permalink is not None:
            left += cloned_permalink
        right = _build_card_toolbar_column(badge_group, name=API.LAYOUT_RIGHT)
        layout += left
        layout += right
        return layout

    top = _build_card_toolbar_column(badge_group, name=API.LAYOUT_TOP)
    bottom = build_api_component(API.LAYOUT_BOTTOM)
    bottom += signature
    if cloned_permalink is not None:
        bottom += cloned_permalink
    layout += top
    layout += bottom
    return layout


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

    The header emits both desktop and mobile layout variants side-by-side
    so theme CSS can container-query between them just like the managed
    ``desc_signature`` path does in ``_transforms``.  Header metadata
    (``data-has-source``, ``data-has-badges``, ``data-badge-count``,
    ``data-has-fold``) is also added so styling can branch on facts the
    cascade can't compute.

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

    header_classes: list[str] = []
    has_source = False  # cards never own a source link today; reserved for future use
    has_badges = badge_group is not None
    has_fold = False  # cards do not currently fold their signatures
    if has_source:
        header_classes.append(API.HEADER_HAS_SOURCE)
    if has_badges:
        header_classes.append(API.HEADER_HAS_BADGES)
    if has_fold:
        header_classes.append(API.HEADER_HAS_FOLD)

    header = build_api_component(
        API.HEADER,
        classes=tuple(header_classes),
        html_attrs={
            "data-has-source": "true" if has_source else "false",
            "data-has-badges": "true" if has_badges else "false",
            "data-badge-count": "1" if has_badges else "0",
            "data-has-fold": "true" if has_fold else "false",
        },
    )

    for variant in ("desktop", "mobile"):
        header += _build_card_layout_variant(
            variant=variant,
            signature_children=signature_children,
            permalink=permalink,
            badge_group=badge_group,
            signature_classes=signature_classes,
        )

    entry += header

    content = build_api_component(API.CONTENT, classes=content_classes)
    for child in content_children:
        content += child
    entry += content
    return entry
