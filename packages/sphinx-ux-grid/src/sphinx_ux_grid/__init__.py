"""CSS-Grid-backed ``{grid}`` and ``{grid-item-card}`` directives.

Provides three directives (``grid``, ``grid-item``, ``grid-item-card``)
that render plain :class:`docutils.nodes.container` trees carrying
``gp-sphinx-grid*`` CSS classes.  Per-directive overrides (column counts,
gutters) are inlined as CSS custom properties on each container's
``style`` attribute, and the bundled stylesheet reads those properties
to drive a CSS Grid layout — no Bootstrap-derived float classes are
emitted, and degradation to text/man/latex falls out of the underlying
``nodes.container`` writer.

Examples
--------
>>> from sphinx_ux_grid import SUG, setup
>>> SUG.GRID
'gp-sphinx-grid'

>>> callable(setup)
True
"""

from __future__ import annotations

import logging
import pathlib
import typing as t

from sphinx.application import Sphinx

from sphinx_ux_grid._css import SUG
from sphinx_ux_grid._directives import (
    GridDirective,
    GridItemCardDirective,
    GridItemDirective,
)
from sphinx_ux_grid._nodes import (
    LinkPassthrough,
    _depart_passthrough,
    _visit_passthrough,
)

__all__ = [
    "SUG",
    "GridDirective",
    "GridItemCardDirective",
    "GridItemDirective",
    "LinkPassthrough",
    "setup",
]

logging.getLogger(__name__).addHandler(logging.NullHandler())

_EXTENSION_VERSION = "0.0.1a18"


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register the three grid directives and the bundled stylesheet.

    Parameters
    ----------
    app : Sphinx
        Sphinx application.

    Returns
    -------
    dict[str, Any]
        Extension metadata.

    Examples
    --------
    >>> from sphinx_ux_grid import setup
    >>> callable(setup)
    True
    """
    app.add_node(
        LinkPassthrough,
        html=(_visit_passthrough, _depart_passthrough),
        latex=(_visit_passthrough, _depart_passthrough),
        text=(_visit_passthrough, _depart_passthrough),
        man=(_visit_passthrough, _depart_passthrough),
        texinfo=(_visit_passthrough, _depart_passthrough),
    )
    app.add_directive("grid", GridDirective)
    app.add_directive("grid-item", GridItemDirective)
    app.add_directive("grid-item-card", GridItemCardDirective)

    _static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if _static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(_static_dir)

    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/sphinx_ux_grid.css")

    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
