"""Shared badge infrastructure for Sphinx autodoc extensions.

Provides :class:`BadgeNode`, HTML visitors, and builder helpers that all
``sphinx-autodoc-*`` packages share instead of reimplementing badges.

Examples
--------
>>> from sphinx_autodoc_badges import BadgeNode, build_badge
>>> callable(build_badge)
True

>>> from sphinx_autodoc_badges import setup
>>> callable(setup)
True
"""

from __future__ import annotations

import logging
import pathlib
import typing as t

from sphinx.application import Sphinx

from sphinx_autodoc_badges._builders import (
    build_badge,
    build_badge_group,
    build_toolbar,
)
from sphinx_autodoc_badges._nodes import BadgeNode
from sphinx_autodoc_badges._visitors import depart_badge_html, visit_badge_html

__all__ = [
    "BadgeNode",
    "build_badge",
    "build_badge_group",
    "build_toolbar",
    "setup",
]

logging.getLogger(__name__).addHandler(logging.NullHandler())

_EXTENSION_VERSION = "0.0.1a5"


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register :class:`BadgeNode` with HTML visitor and shared CSS.

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
    >>> from sphinx_autodoc_badges import setup
    >>> callable(setup)
    True
    """
    app.add_node(BadgeNode, html=(visit_badge_html, depart_badge_html))

    _static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if _static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(_static_dir)

    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/sphinx_autodoc_badges.css")

    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
