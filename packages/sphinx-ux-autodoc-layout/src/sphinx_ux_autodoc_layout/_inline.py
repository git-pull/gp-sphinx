"""Inline value rendering for shared fact rows.

Fact bodies frequently hold lists of short code values (output formats,
transform classes, overridden handlers). Rendering them as one
comma-joined literal produces a single wrapping blob and makes every
name dead text. These helpers render each value as its own literal
"chip" and, where a value names a documented Python object, wrap the
chip in a py-domain cross-reference that resolves when a target exists
and silently stays a literal when it does not.
"""

from __future__ import annotations

import typing as t

from docutils import nodes
from sphinx import addnodes

if t.TYPE_CHECKING:
    from collections.abc import Sequence

#: Em dash rendered when a fact has no values.
EMPTY_VALUE = "—"


def build_linked_literal(
    target: str,
    display: str | None = None,
) -> addnodes.pending_xref:
    """Return a literal chip wrapped in a py-domain cross-reference.

    The reference resolves against any documented Python object
    (``reftype="obj"`` covers classes, methods, functions, …) using the
    fully-qualified *target*. When no target exists the literal renders
    unchanged and, because ``refwarn`` stays false, no warning is
    emitted — externals like docutils base classes (which publish no
    intersphinx inventory) degrade gracefully.

    Parameters
    ----------
    target : str
        Fully-qualified dotted path to resolve against.
    display : str | None
        Chip text; defaults to *target*.

    Returns
    -------
    addnodes.pending_xref
        Cross-reference wrapping a single literal chip.

    Examples
    --------
    >>> xref = build_linked_literal("pkg.mod.Cls")
    >>> xref["reftarget"]
    'pkg.mod.Cls'
    >>> xref["refdomain"], xref["reftype"], xref["refwarn"]
    ('py', 'obj', False)
    >>> xref.astext()
    'pkg.mod.Cls'

    >>> build_linked_literal("pkg.mod.Cls.visit_table", "visit_table").astext()
    'visit_table'
    """
    text = display if display is not None else target
    literal = nodes.literal(
        "",
        "",
        nodes.Text(text),
        classes=["xref", "py", "py-obj"],
    )
    return addnodes.pending_xref(
        "",
        literal,
        refdomain="py",
        reftype="obj",
        reftarget=target,
        refexplicit=display is not None,
        refwarn=False,
    )


def build_chip_paragraph(
    items: Sequence[nodes.Node | str],
) -> nodes.paragraph:
    """Return a paragraph of comma-separated inline chips.

    Strings become plain literal chips; nodes (e.g. from
    :func:`build_linked_literal`) are inserted as-is. An empty sequence
    renders a single em-dash literal so callers keep the shared
    "no value" presentation.

    Parameters
    ----------
    items : Sequence[nodes.Node | str]
        Chip values in display order.

    Returns
    -------
    nodes.paragraph
        Paragraph holding the chips.

    Examples
    --------
    >>> paragraph = build_chip_paragraph(["html5", "xhtml", "html"])
    >>> paragraph.astext()
    'html5, xhtml, html'
    >>> sum(isinstance(child, nodes.literal) for child in paragraph.children)
    3

    >>> build_chip_paragraph([]).astext()
    '—'

    >>> mixed = build_chip_paragraph([build_linked_literal("pkg.Cls"), "raw"])
    >>> mixed.astext()
    'pkg.Cls, raw'
    """
    paragraph = nodes.paragraph()
    if not items:
        paragraph += nodes.literal(EMPTY_VALUE, EMPTY_VALUE)
        return paragraph
    for index, item in enumerate(items):
        if index:
            paragraph += nodes.Text(", ")
        if isinstance(item, str):
            paragraph += nodes.literal(item, item)
        else:
            paragraph += item
    return paragraph
