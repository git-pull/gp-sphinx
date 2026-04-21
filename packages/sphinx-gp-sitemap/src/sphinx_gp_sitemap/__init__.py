"""Sitemap generator for Sphinx.

Drop-in replacement for ``sphinx-sitemap`` with Sphinx 8.1+ idioms, a
plain ``list`` in ``env.temp_data`` instead of ``multiprocessing.Queue``,
and ``app.builder.name`` based builder detection instead of a monkey
patch.

The scaffolding commit registers a ``setup()`` that is importable and
loadable by Sphinx but does not yet connect any hooks. Subsequent commits
add the config values and XML emission chain.

Examples
--------
>>> from sphinx_gp_sitemap import setup
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
    >>> from sphinx_gp_sitemap import setup
    >>> callable(setup)
    True
    """
    del app  # placeholder until hooks are connected
    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
