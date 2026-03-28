"""Sphinx extensions for CLI/argparse documentation.

Provides lexers, roles, and directives for documenting argparse-based
CLI tools in Sphinx. Use as a Sphinx extension via::

    extra_extensions=["gp_sphinx.ext.argparse"]

Or in conf.py::

    extensions = ["gp_sphinx.ext.argparse"]

Examples
--------
>>> from gp_sphinx.ext.argparse import setup

>>> callable(setup)
True
"""

from __future__ import annotations

import pathlib
import typing as t

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

STATIC_DIR = pathlib.Path(__file__).parent
"""Path to the argparse extension directory (contains highlight.css)."""


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register argparse lexers, roles, directives, and CSS.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application object.

    Returns
    -------
    dict[str, Any]
        Extension metadata.
    """
    from gp_sphinx.ext.argparse.cli_usage_lexer import CLIUsageLexer
    from gp_sphinx.ext.argparse.lexer import ArgparseLexer
    from gp_sphinx.ext.argparse.neo import setup as neo_setup
    from gp_sphinx.ext.argparse.roles import setup as roles_setup

    # Register lexers
    app.add_lexer("argparse", ArgparseLexer)
    app.add_lexer("cli-usage", CLIUsageLexer)

    # Register argparse-neo directives
    neo_setup(app)

    # Register roles
    roles_setup(app)

    # Add CSS for argparse syntax highlighting
    css_path = STATIC_DIR / "highlight.css"
    if css_path.is_file():
        app.add_css_file("css/argparse-highlight.css")

    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
