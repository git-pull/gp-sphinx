"""Diagnostic error types raised by the backend and extension.

Each error carries a multi-line, copy-pasteable hint so the failure is
fixable from the message itself. The PEP 517 backend re-raises these as
their own type (so build frontends like pip / uv display the full
message); the Sphinx extension re-wraps them in
:class:`sphinx.errors.ConfigError` so Sphinx halts the build with the
same content.
"""

from __future__ import annotations


class SphinxViteBuilderError(Exception):
    """Base class for all sphinx-vite-builder-raised diagnostic errors."""


class PnpmMissingError(SphinxViteBuilderError):
    """Raised when ``pnpm`` is not on ``PATH``.

    pnpm is not pip-installable, so the backend cannot bootstrap it the
    way maturin bootstraps Rust via ``puccinialin``. The hint surfaces
    the canonical install paths (``corepack enable``, the pnpm.io
    install URL) so the user has an actionable next step.
    """


class NodeModulesInstallError(SphinxViteBuilderError):
    """Raised when ``pnpm install`` exits non-zero.

    Surfaces the install command that failed and a re-run recipe. Callers
    should attach the captured stderr to the message before raising so
    the underlying pnpm diagnostic is visible at the call site.
    """


class ViteFailedError(SphinxViteBuilderError):
    """Raised when ``pnpm exec vite build`` exits non-zero.

    Surfaces the vite invocation that failed plus context (cwd, exit
    code). Callers should attach the captured stderr.
    """
