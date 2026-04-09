"""Sphinx extension for enhanced Python API entry styling.

Injects badge groups (type + modifier badges) into standard Python domain
``desc`` nodes (functions, classes, methods, properties, attributes, etc.)
and registers CSS for card-style containers that match the fixture styling
from ``sphinx_autodoc_pytest_fixtures``.

Badge types:
    - **Type badges** (rightmost): function, class, method, property,
      attribute, data, exception
    - **Modifier badges** (left of type): async, classmethod, staticmethod,
      abstract, final, deprecated

.. note::

   This extension self-registers its CSS via ``add_css_file()``.  The rules
   live in ``_static/css/api_style.css`` inside this package.

Examples
--------
>>> from sphinx_autodoc_api_style import setup
>>> callable(setup)
True

>>> from sphinx_autodoc_api_style._css import _CSS
>>> _CSS.BADGE_GROUP
'gas-badge-group'
"""

from __future__ import annotations

import logging
import pathlib
import typing as t

from sphinx_autodoc_api_style._badges import build_badge_group
from sphinx_autodoc_api_style._css import _CSS
from sphinx_autodoc_api_style._transforms import on_doctree_resolved

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = [
    "_CSS",
    "build_badge_group",
    "setup",
]

logging.getLogger(__name__).addHandler(logging.NullHandler())

_EXTENSION_VERSION = "1.0"


class _SetupDict(t.TypedDict):
    """Return type for Sphinx extension ``setup()``."""

    version: str
    parallel_read_safe: bool
    parallel_write_safe: bool


def setup(app: Sphinx) -> _SetupDict:
    """Register the ``sphinx_autodoc_api_style`` extension.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application instance.

    Returns
    -------
    _SetupDict
        Extension metadata dict.

    Examples
    --------
    >>> callable(setup)
    True
    """
    app.setup_extension("sphinx.ext.autodoc")
    app.setup_extension("sphinx_autodoc_badges")
    app.setup_extension("sphinx_autodoc_layout")

    _static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if _static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(_static_dir)

    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/api_style.css")

    app.connect("doctree-resolved", on_doctree_resolved)

    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
