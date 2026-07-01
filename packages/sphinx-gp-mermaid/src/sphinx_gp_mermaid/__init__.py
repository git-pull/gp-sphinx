"""Build-time mermaid rendering for Sphinx, producing inline SVG.

Renders fenced ``mermaid`` blocks to inline ``<svg>`` at build time via
``mmdc`` (`@mermaid-js/mermaid-cli`_), so diagrams paint with the page: there
is no client-side mermaid runtime, no asynchronous pop-in, and no layout
shift. Each diagram is rendered twice — a light and a dark variant — and both
are inlined, toggled by CSS on ``body[data-theme]``.

Examples
--------
>>> from sphinx_gp_mermaid import setup
>>> callable(setup)
True

.. _`@mermaid-js/mermaid-cli`: https://github.com/mermaid-js/mermaid-cli
"""

from __future__ import annotations

import logging
import typing as t

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata

_EXTENSION_VERSION = "0.0.1a31"

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = ["setup"]


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the mermaid directive, node, config values, and stylesheet.

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
    >>> from sphinx_gp_mermaid import setup
    >>> callable(setup)
    True
    """
    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
