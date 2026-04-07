"""Doctree transforms for componentized autodoc layout.

Runs as a ``doctree-resolved`` event handler at priority 600, after
``sphinx-autodoc-api-style`` (priority 500).  Wraps contiguous runs
of ``desc_content`` children into ``gal_region`` nodes and optionally
folds large field-list regions into ``gal_fold`` disclosure blocks.

Examples
--------
>>> from sphinx_autodoc_layout._transforms import _classify_child
>>> from docutils import nodes
>>> _classify_child(nodes.paragraph())
'narrative'
>>> _classify_child(nodes.field_list())
'fields'
"""

from __future__ import annotations

import logging
import typing as t

from docutils import nodes
from sphinx import addnodes

from sphinx_autodoc_layout._nodes import gal_fold, gal_region

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)

_SKIP_FOLD_OBJTYPES: frozenset[str] = frozenset(
    {
        "attribute",
        "data",
        "fixture",
        "module",
        "property",
    }
)


def _classify_child(child: nodes.Node) -> str:
    """Classify a ``desc_content`` child by its node type.

    Parameters
    ----------
    child : nodes.Node
        A direct child of ``desc_content``.

    Returns
    -------
    str
        One of ``"fields"``, ``"members"``, or ``"narrative"``.

    Examples
    --------
    >>> from docutils import nodes
    >>> from sphinx import addnodes
    >>> _classify_child(nodes.field_list())
    'fields'
    >>> _classify_child(addnodes.desc())
    'members'
    >>> _classify_child(nodes.paragraph())
    'narrative'
    >>> _classify_child(nodes.note())
    'narrative'
    """
    if isinstance(child, nodes.field_list):
        return "fields"
    if isinstance(child, addnodes.desc):
        return "members"
    return "narrative"


def _wrap_content_runs(desc_node: addnodes.desc) -> None:
    """Wrap contiguous runs of ``desc_content`` children in regions.

    Iterates children in order, grouping contiguous same-type nodes
    into ``gal_region`` wrappers.  Never reorders children.

    Parameters
    ----------
    desc_node : addnodes.desc
        The description node to restructure.

    Examples
    --------
    >>> from docutils import nodes
    >>> from sphinx import addnodes
    >>> desc = addnodes.desc(domain="py", objtype="function")
    >>> sig = addnodes.desc_signature()
    >>> desc += sig
    >>> content = addnodes.desc_content()
    >>> content += nodes.paragraph("", "hello")
    >>> content += nodes.field_list()
    >>> desc += content
    >>> _wrap_content_runs(desc)
    >>> len(content.children)
    2
    >>> isinstance(content.children[0], gal_region)
    True
    >>> content.children[0].get("kind")
    'narrative'
    >>> content.children[1].get("kind")
    'fields'
    """
    content = next(
        (c for c in desc_node.children if isinstance(c, addnodes.desc_content)),
        None,
    )
    if content is None or not content.children:
        return

    original = list(content.children)
    content.children = []

    current_kind: str | None = None
    current_region: gal_region | None = None

    for child in original:
        kind = _classify_child(child)
        if kind != current_kind:
            if current_region is not None:
                content += current_region
            current_region = gal_region(kind=kind)
            current_kind = kind
        assert current_region is not None
        current_region += child

    if current_region is not None:
        content += current_region


def _count_field_entries(field_list: nodes.field_list) -> int:
    """Count individual entries in a Sphinx field list.

    Sphinx's ``DocFieldTransformer`` collapses multiple params into a
    single ``field`` containing a ``bullet_list`` of ``list_item``
    nodes.  This function counts ``list_item`` nodes inside collapsed
    fields plus standalone ``field`` nodes.

    Parameters
    ----------
    field_list : nodes.field_list
        The field list to count.

    Returns
    -------
    int
        Total entry count.

    Examples
    --------
    Collapsed (Sphinx-style) — single field with bullet_list:

    >>> from docutils import nodes
    >>> fl = nodes.field_list()
    >>> f = nodes.field()
    >>> f += nodes.field_name("", "Parameters")
    >>> body = nodes.field_body()
    >>> bl = nodes.bullet_list()
    >>> for i in range(5):
    ...     bl += nodes.list_item("", nodes.paragraph("", f"p{i}"))
    >>> body += bl
    >>> f += body
    >>> fl += f
    >>> _count_field_entries(fl)
    5

    Non-collapsed — individual fields:

    >>> fl2 = nodes.field_list()
    >>> for i in range(3):
    ...     f2 = nodes.field()
    ...     f2 += nodes.field_name("", f"p{i}")
    ...     f2 += nodes.field_body("", nodes.paragraph("", "..."))
    ...     fl2 += f2
    >>> _count_field_entries(fl2)
    3
    """
    count = 0
    for field in field_list.children:
        if not isinstance(field, nodes.field):
            continue
        # Check if field body contains a bullet_list (collapsed params)
        for body_child in field.children:
            if isinstance(body_child, nodes.field_body):
                for item in body_child.children:
                    if isinstance(item, nodes.bullet_list):
                        count += sum(
                            1 for li in item.children if isinstance(li, nodes.list_item)
                        )
                        break
                else:
                    # No bullet_list found — count the field itself
                    count += 1
                break
        else:
            count += 1
    return count


def _fold_large_field_regions(
    content: addnodes.desc_content,
    threshold: int,
) -> None:
    """Wrap large ``field_list`` nodes in ``gal_fold`` disclosure blocks.

    Only folds ``gal_region(kind="fields")`` children whose
    ``field_list`` contains enough entries to exceed *threshold*.

    Sphinx's ``DocFieldTransformer`` collapses multiple params into a
    single ``field`` with a ``bullet_list`` of ``list_item`` children.
    We count ``list_item`` nodes (individual params) plus standalone
    ``field`` nodes (Returns, Raises) to get the total entry count.

    Parameters
    ----------
    content : addnodes.desc_content
        The description content node (already wrapped in regions).
    threshold : int
        Minimum entry count to trigger folding.

    Examples
    --------
    Sphinx-style collapsed field list (single field with bullet_list):

    >>> from docutils import nodes
    >>> from sphinx import addnodes
    >>> content = addnodes.desc_content()
    >>> region = gal_region(kind="fields")
    >>> fl = nodes.field_list()
    >>> f = nodes.field()
    >>> f += nodes.field_name("", "Parameters")
    >>> body = nodes.field_body()
    >>> bl = nodes.bullet_list()
    >>> for i in range(12):
    ...     bl += nodes.list_item("", nodes.paragraph("", f"p{i}"))
    >>> body += bl
    >>> f += body
    >>> fl += f
    >>> region += fl
    >>> content += region
    >>> _fold_large_field_regions(content, threshold=10)
    >>> fold = region.children[0]
    >>> isinstance(fold, gal_fold)
    True
    >>> fold.get("summary")
    'Parameters (12)'
    """
    for region in content.children:
        if not isinstance(region, gal_region):
            continue
        if region.get("kind") != "fields":
            continue
        for field_list in list(region.children):
            if not isinstance(field_list, nodes.field_list):
                continue
            entry_count = _count_field_entries(field_list)
            if entry_count < threshold:
                continue
            fold = gal_fold(
                kind="parameters",
                summary=f"Parameters ({entry_count})",
            )
            idx = region.children.index(field_list)
            region.remove(field_list)
            fold += field_list
            region.insert(idx, fold)


def on_doctree_resolved(
    app: Sphinx,
    doctree: nodes.document,
    docname: str,
) -> None:
    """Restructure autodoc ``desc_content`` into semantic regions.

    Connected to ``doctree-resolved`` at priority 600, after
    ``sphinx-autodoc-api-style`` (priority 500).

    Parameters
    ----------
    app : Sphinx
        The Sphinx application.
    doctree : nodes.document
        The resolved doctree.
    docname : str
        The document name.

    Examples
    --------
    >>> on_doctree_resolved  # doctest: +ELLIPSIS
    <function on_doctree_resolved at 0x...>
    """
    if not app.config.gal_enabled:
        return
    if getattr(app.builder, "format", "") != "html":
        return

    threshold: int = app.config.gal_collapsed_threshold
    fold_params: bool = app.config.gal_fold_parameters

    for desc_node in doctree.findall(addnodes.desc):
        if desc_node.get("domain") != "py":
            continue

        _wrap_content_runs(desc_node)

        if fold_params:
            objtype = desc_node.get("objtype", "")
            if objtype not in _SKIP_FOLD_OBJTYPES:
                content = next(
                    (
                        c
                        for c in desc_node.children
                        if isinstance(c, addnodes.desc_content)
                    ),
                    None,
                )
                if content is not None:
                    _fold_large_field_regions(content, threshold)
