"""OpenGraph and Twitter meta-tag emission for Sphinx.

Drop-in replacement for ``sphinxext-opengraph`` with the same ``ogp_*``
configuration surface, minus the matplotlib-based social-card generator.

The scaffolding commit registers a ``setup()`` that is importable and
loadable by Sphinx but does not yet connect any hooks. Subsequent commits
port the description / title / meta helpers and wire the
``html-page-context`` emitter.

Examples
--------
>>> from sphinx_gp_opengraph import setup
>>> callable(setup)
True
"""

from __future__ import annotations

import typing as t

from sphinx.application import Sphinx

_EXTENSION_VERSION = "0.0.1a9"

__all__ = ["setup"]


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register the extension; currently a no-op placeholder.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance (unused in the scaffold).

    Returns
    -------
    dict[str, Any]
        Extension metadata — version plus parallel-build flags.

    Examples
    --------
    >>> from sphinx_gp_opengraph import setup
    >>> callable(setup)
    True
    """
    del app  # placeholder until hooks are connected
    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
