"""sphinx-vite-builder: PEP 517 backend + Sphinx extension.

Two orthogonal entry points share one subprocess core:

- :mod:`sphinx_vite_builder.build` — the PEP 517 backend module that
  consumer packages reference via
  ``[build-system].build-backend = "sphinx_vite_builder.build"``.
- :func:`sphinx_vite_builder.setup` — the Sphinx extension entry point
  that ``conf.py`` references via
  ``extensions = ["sphinx_vite_builder"]``.

Neither head calls the other; they share the implementation modules
under :mod:`sphinx_vite_builder._internal`.
"""

from __future__ import annotations

import logging
import typing as t

__version__ = "0.0.1a16.dev1"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register the Sphinx-extension head.

    Phase 1 ships the PEP 517 backend; the extension head's full
    implementation (vite watch on ``sphinx-autobuild``, one-shot build
    on ``sphinx-build``) lands in a follow-up commit. For now this
    stub registers the extension so consumers can declare it without
    a no-such-module error, and returns the safety metadata.
    """
    del app
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": __version__,
    }


__all__ = ("__version__", "setup")
