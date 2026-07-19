"""Reusable Sphinx highlighting helpers.

Registers documentation-oriented Pygments lexers and inline literal
helpers for Sphinx projects.

Examples
--------
>>> from sphinx_gp_highlighting import setup
>>> callable(setup)
True
"""

from __future__ import annotations

import logging
import pathlib
import typing as t

from sphinx.util.logging import getLogger

from sphinx_gp_highlighting.inline import (
    HighlightingInlineTransform,
    cmd_role,
    dir_role,
    path_role,
)
from sphinx_gp_highlighting.lexers import DirectoryTreeLexer

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata

_EXTENSION_VERSION = "0.0.1a35"
_TREE_ALIASES: tuple[str, ...] = ("tree", "directory-tree", "dir-tree")

logger = getLogger(__name__)
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = ["DirectoryTreeLexer", "HighlightingInlineTransform", "setup"]


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the package lexers with Sphinx.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.

    Returns
    -------
    ExtensionMetadata
        Extension metadata with version and parallel-build flags.

    Examples
    --------
    >>> from sphinx_gp_highlighting import setup
    >>> callable(setup)
    True
    """
    for alias in _TREE_ALIASES:
        app.add_lexer(alias, DirectoryTreeLexer)
    app.add_config_value(
        "gp_highlighting_inline_literals",
        default="off",
        rebuild="env",
        types=frozenset({str}),
        description=(
            "Inline literal auto-highlighting mode. Use ``'safe'`` to "
            "highlight configured commands and clear path/directory literals."
        ),
    )
    app.add_config_value(
        "gp_highlighting_inline_commands",
        default=[],
        rebuild="env",
        types=frozenset({list, tuple}),
        description=(
            "Command names eligible for safe inline literal highlighting "
            "when ``gp_highlighting_inline_literals`` is ``'safe'``."
        ),
    )
    app.add_role("cmd", cmd_role)
    app.add_role("path", path_role)
    app.add_role("dir", dir_role)
    app.add_transform(HighlightingInlineTransform)

    static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(static_dir)

    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/sphinx_gp_highlighting.css")
    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
