"""Curated GitHub Octicons as a Sphinx ``{octicon}`` role.

Ships a small audited set of icons under the ``gp-sphinx-octicon`` CSS
namespace and registers the ``octicon`` role so MyST and reStructuredText
sources can call it as a drop-in replacement for sphinx-design's
implementation.

Examples
--------
>>> from sphinx_ux_octicons import render_octicon, setup
>>> svg = render_octicon("rocket")
>>> "gp-sphinx-octicon--rocket" in svg
True
>>> callable(setup)
True
"""

from __future__ import annotations

import logging
import pathlib
import typing as t

from sphinx.application import Sphinx

from sphinx_ux_octicons._nodes import OcticonNode
from sphinx_ux_octicons._render import load_octicons, render_octicon
from sphinx_ux_octicons._role import OcticonRole
from sphinx_ux_octicons._visitors import visit_octicon_html

__all__ = [
    "OcticonNode",
    "OcticonRole",
    "load_octicons",
    "render_octicon",
    "setup",
]

logging.getLogger(__name__).addHandler(logging.NullHandler())

_EXTENSION_VERSION = "0.0.1a18"


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register the ``octicon`` role, the :class:`OcticonNode`, and shared CSS.

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
    >>> from sphinx_ux_octicons import setup
    >>> callable(setup)
    True
    """
    app.add_node(OcticonNode, html=(visit_octicon_html, None))
    app.add_role("octicon", OcticonRole())

    _static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if _static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(_static_dir)

    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/sphinx_ux_octicons.css")

    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
