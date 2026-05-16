"""Sphinx event handlers that run the synchronous Vite build.

Lifecycle:

- ``builder-inited`` (:func:`on_builder_inited`) — resolve config, run
  ``pnpm exec vite build`` synchronously (via :func:`run_vite_build`),
  then return so Sphinx's static-file copying picks up fresh CSS/JS.
- ``build-finished`` (:func:`on_build_finished`) — log exceptions; no
  cleanup needed because the build is one-shot.

The build runs synchronously because under ``sphinx-autobuild``, each
build executes in a short-lived subprocess (per
:mod:`sphinx_autobuild.build`); an async vite watch would race
Sphinx's ``copy_static_files`` phase and Sphinx would copy stale
assets. A ~600ms blocking call per rebuild is the trade for
guaranteed-fresh CSS/JS.
"""

from __future__ import annotations

import typing as t

from sphinx.errors import ExtensionError
from sphinx.util import logging as sphinx_logging

from .config import SphinxViteBuilderConfig, detect_mode, resolve_vite_root
from .errors import SphinxViteBuilderError
from .vite import run_vite_build

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

# `sphinx.util.logging.getLogger` returns a SphinxLoggerAdapter that
# routes through Sphinx's status / warning streams — which means our
# `[vite] …` lines actually surface in `sphinx-autobuild` output the
# same way Sphinx's own messages do. The stdlib `logging.getLogger`
# does not propagate by default in Sphinx contexts.
logger = sphinx_logging.getLogger(__name__)


def _raise_as_extension_error(exc: Exception) -> t.NoReturn:
    """Re-raise ``exc`` as :class:`sphinx.errors.ExtensionError`.

    Sphinx's ``EventManager.emit()`` (``sphinx/events.py:405-456``)
    auto-wraps non-``SphinxError`` exceptions raised from event handlers
    using ``safe_getattr(listener.handler, '__module__', None)`` for the
    ``modname`` kwarg — which for our hooks resolves to
    ``'sphinx_vite_builder._internal.hooks'``. Wrapping explicitly with
    ``modname='sphinx_vite_builder'`` keeps the user-facing
    ``Extension error (sphinx_vite_builder)`` category clean and points
    consumers at the published package, not the internal module path.
    Because :class:`ExtensionError` IS a :class:`SphinxError`, the
    auto-wrap path skips it: no double-wrap risk.
    """
    raise ExtensionError(
        str(exc),
        orig_exc=exc,
        modname="sphinx_vite_builder",
    ) from exc


def _build_config(app: Sphinx) -> SphinxViteBuilderConfig:
    """Snapshot the live config values into a frozen dataclass."""
    return SphinxViteBuilderConfig(
        mode=detect_mode(config_value=app.config.sphinx_vite_builder_mode),
        vite_root=resolve_vite_root(app.config.sphinx_vite_builder_root),
    )


def on_builder_inited(app: Sphinx) -> None:
    """``builder-inited`` event handler.

    Runs ``pnpm exec vite build`` synchronously and blocks until it
    finishes. Both PROD (plain ``sphinx-build``) and DEV
    (``sphinx-autobuild``) take this same path: each ``sphinx-autobuild``
    rebuild is a fresh subprocess, so a synchronous one-shot vite per
    rebuild is the correct primitive — it guarantees Sphinx's
    ``copy_static_files`` phase sees fresh CSS/JS rather than racing an
    async watch that hasn't finished its initial build yet.

    :func:`run_vite_build` handles the ``SPHINX_VITE_BUILDER_SKIP``
    escape hatch, the ``web/``-absent short-circuit, missing
    ``node_modules`` auto-install, and fast-fail diagnostics
    (``PnpmMissingError`` / ``NodeModulesInstallError`` /
    ``ViteFailedError``) internally; this hook just funnels Sphinx's
    extension-error path through ``_raise_as_extension_error``.
    """
    config = _build_config(app)
    if config.vite_root is None:
        # No vite_root configured → nothing to orchestrate (typical when
        # running off an installed wheel with the static tree pre-baked).
        return

    # ``run_vite_build`` resolves ``web/`` relative to its
    # ``project_root`` argument, so pass the parent of vite_root.
    try:
        run_vite_build(project_root=config.vite_root.parent)
    except SphinxViteBuilderError as exc:
        _raise_as_extension_error(exc)


def on_build_finished(app: Sphinx, exception: BaseException | None) -> None:
    """``build-finished`` event handler.

    No-op for the common case. Logs the exception (if any) for
    context, but does not interfere with Sphinx's own error reporting.
    """
    if exception is not None:
        logger.debug(
            "[vite] sphinx build finished with exception: %s",
            exception,
        )
