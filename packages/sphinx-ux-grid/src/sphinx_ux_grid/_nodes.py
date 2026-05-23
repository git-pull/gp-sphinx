"""Custom node types for sphinx_ux_grid.

The only custom node :class:`LinkPassthrough` is a thin wrapper around
:class:`docutils.nodes.TextElement` that exists so a card's stretched
link node has a parent the HTML writer recognizes as a text element.
It emits no markup of its own — its children render directly.

Examples
--------
>>> from sphinx_ux_grid._nodes import LinkPassthrough
>>> issubclass(LinkPassthrough, object)
True
"""

from __future__ import annotations

import typing as t

from docutils import nodes


class LinkPassthrough(nodes.TextElement):
    """Inline text-element carrier for a card's stretched-link node.

    Sphinx's HTML5 writer assumes a :class:`nodes.reference` or
    :class:`sphinx.addnodes.pending_xref` lives inside a
    :class:`nodes.TextElement`; wrapping the stretched link in this
    passthrough lets such a node sit as a card child without triggering
    the writer's image-only assertion path.

    The visitors registered for this node emit nothing — children render
    in place.

    Examples
    --------
    >>> from sphinx_ux_grid._nodes import LinkPassthrough
    >>> issubclass(LinkPassthrough, nodes.TextElement)
    True
    """


def _visit_passthrough(self: t.Any, node: nodes.Node) -> None:
    """Emit nothing for :class:`LinkPassthrough` — children render in place."""


def _depart_passthrough(self: t.Any, node: nodes.Node) -> None:
    """Emit nothing on departure — children have already been rendered."""


__all__ = [
    "LinkPassthrough",
    "_depart_passthrough",
    "_visit_passthrough",
]
