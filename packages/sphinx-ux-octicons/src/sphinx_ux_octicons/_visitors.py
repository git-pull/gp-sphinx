"""HTML5 visitor for :class:`OcticonNode`.

The visitor writes the pre-rendered SVG payload directly into the HTML
output and raises :class:`docutils.nodes.SkipNode` so docutils does not
descend into the :class:`docutils.nodes.Text` child carrying the icon
name fallback for non-HTML builders.
"""

from __future__ import annotations

import typing as t

from docutils import nodes

if t.TYPE_CHECKING:
    from sphinx.writers.html5 import HTML5Translator

    from sphinx_ux_octicons._nodes import OcticonNode


def visit_octicon_html(self: HTML5Translator, node: OcticonNode) -> None:
    """Emit the pre-rendered SVG markup and skip child rendering.

    Parameters
    ----------
    self : HTML5Translator
        Active HTML writer instance.
    node : OcticonNode
        Octicon node carrying ``svg_markup``.

    Raises
    ------
    docutils.nodes.SkipNode
        Always, after writing the SVG payload, to prevent docutils from
        rendering the icon-name :class:`docutils.nodes.Text` fallback
        child into HTML output.

    Examples
    --------
    >>> from sphinx_ux_octicons._nodes import OcticonNode
    >>> node = OcticonNode("rocket", svg_markup="<svg/>")
    >>> node["svg_markup"]
    '<svg/>'
    """
    self.body.append(node["svg_markup"])
    raise nodes.SkipNode
