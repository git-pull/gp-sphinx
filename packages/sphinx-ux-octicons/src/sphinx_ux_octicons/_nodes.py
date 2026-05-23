"""``OcticonNode`` -- docutils node for inline GitHub octicons.

Subclasses :class:`docutils.nodes.inline` so unregistered builders (text,
LaTeX, man) fall back to ``visit_inline`` via Sphinx's MRO-based
dispatch and render the icon name surrogate carried as a
:class:`docutils.nodes.Text` child.

The HTML visitor emits the pre-rendered SVG payload stored on
``node["svg_markup"]`` directly and skips descent, so the text child
never leaks into HTML output.

Examples
--------
>>> node = OcticonNode("rocket", svg_markup="<svg></svg>")
>>> node.astext()
'rocket'

>>> node["svg_markup"]
'<svg></svg>'
"""

from __future__ import annotations

import typing as t

from docutils import nodes


class OcticonNode(nodes.inline):
    """Inline node carrying a pre-rendered octicon SVG and a name fallback.

    The HTML visitor reads ``node["svg_markup"]`` and writes the SVG into
    the document body before raising :class:`docutils.nodes.SkipNode`.
    Other builders rely on docutils' MRO dispatch to ``visit_inline`` and
    render the :class:`docutils.nodes.Text` child holding the icon name.

    Parameters
    ----------
    name : str
        Icon name; rendered as visible fallback text for non-HTML
        builders.
    svg_markup : str
        Pre-rendered inline SVG string produced by
        :func:`sphinx_ux_octicons._render.render_octicon`.
    **attributes : Any
        Additional docutils node attributes.

    Examples
    --------
    >>> node = OcticonNode("alert", svg_markup="<svg>...</svg>")
    >>> node.astext()
    'alert'

    >>> "<svg>" in node["svg_markup"]
    True
    """

    def __init__(
        self,
        name: str = "",
        *,
        svg_markup: str = "",
        **attributes: t.Any,
    ) -> None:
        children = [nodes.Text(name)] if name else []
        super().__init__("", *children, **attributes)
        self["svg_markup"] = svg_markup
