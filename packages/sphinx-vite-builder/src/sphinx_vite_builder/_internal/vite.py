"""Vite + pnpm orchestration: detection, install, one-shot build, watch.

This module is the shared orchestration core consumed by both heads:

- The PEP 517 backend (:mod:`sphinx_vite_builder.build`) calls
  :func:`run_vite_build` from each of its hooks, before delegating to
  hatchling.
- The Sphinx extension (:mod:`sphinx_vite_builder`) calls
  :func:`run_vite_build` (one-shot) or its watch sibling from
  ``builder-inited``.

Fast-fail discipline: every prerequisite is checked up front so the
caller gets an actionable diagnostic instead of a generic spawn-failure
deep in the asyncio plumbing.
"""

from __future__ import annotations

import logging
import os
import pathlib
import shutil
import textwrap
import typing as t

from .bus import AsyncioBus
from .errors import (
    NodeModulesInstallError,
    PnpmMissingError,
    ViteFailedError,
)
from .process import AsyncProcess

logger = logging.getLogger(__name__)


def pnpm_install_command(*, package_manager: str = "pnpm") -> tuple[str, ...]:
    """Build the canonical "install workspace deps" argv.

    ``--frozen-lockfile`` matches the workspace's pinned ``pnpm-lock.yaml``;
    pnpm refuses to mutate the lockfile or auto-resolve unspecified deps,
    so the install is reproducible across machines and CI.

    Examples
    --------
    >>> pnpm_install_command()
    ('pnpm', 'install', '--frozen-lockfile')
    >>> pnpm_install_command(package_manager="npm")
    ('npm', 'install', '--frozen-lockfile')
    """
    return (package_manager, "install", "--frozen-lockfile")


def vite_build_command(*, package_manager: str = "pnpm") -> tuple[str, ...]:
    """Build the canonical one-shot "vite build" argv.

    Examples
    --------
    >>> vite_build_command()
    ('pnpm', 'exec', 'vite', 'build')
    >>> vite_build_command(package_manager="npm")
    ('npm', 'exec', 'vite', 'build')
    """
    return (package_manager, "exec", "vite", "build")


def vite_watch_command(*, package_manager: str = "pnpm") -> tuple[str, ...]:
    """Build the canonical Vite-watch argv.

    Examples
    --------
    >>> vite_watch_command()
    ('pnpm', 'exec', 'vite', 'build', '--watch')
    >>> vite_watch_command(package_manager="npm")
    ('npm', 'exec', 'vite', 'build', '--watch')
    """
    return (package_manager, "exec", "vite", "build", "--watch")


def _format_pnpm_missing_hint(vite_root: pathlib.Path) -> str:
    """Multi-line, copy-pasteable hint when pnpm is not on PATH."""
    return textwrap.dedent(
        f"""\
        sphinx-vite-builder: cannot bootstrap the vite toolchain.
        `pnpm` is not on PATH. Install it via one of:

          corepack enable        # Node 16.10+ ships corepack
          curl -fsSL https://get.pnpm.io/install.sh | sh -

        See https://pnpm.io/installation

        Then re-run with `pnpm` available, or, if this environment is not
        supposed to build assets (e.g. a wheel-only install with the
        static tree pre-baked), set `SPHINX_VITE_BUILDER_SKIP=1`.

        Vite project root resolved to: {vite_root}
        """,
    ).rstrip()


def _format_install_failed_hint(
    *,
    vite_root: pathlib.Path,
    install_cmd: tuple[str, ...],
    returncode: int,
    stderr: str,
) -> str:
    """Multi-line hint when ``pnpm install`` exits non-zero."""
    cmd_str = " ".join(install_cmd)
    stderr_block = stderr.strip() or "(no stderr captured)"
    return textwrap.dedent(
        f"""\
        sphinx-vite-builder: `{cmd_str}` exited with code {returncode} in {vite_root}.
        The vite-managed theme assets cannot be produced; aborting the
        build rather than shipping unstyled docs.

        Fix:
          cd {vite_root}
          {cmd_str}

        Captured stderr:
        {textwrap.indent(stderr_block, "  ")}
        """,
    ).rstrip()


def _format_vite_failed_hint(
    *,
    vite_root: pathlib.Path,
    build_cmd: tuple[str, ...],
    returncode: int,
    stderr: str,
) -> str:
    """Multi-line hint when ``pnpm exec vite build`` exits non-zero."""
    cmd_str = " ".join(build_cmd)
    stderr_block = stderr.strip() or "(no stderr captured)"
    return textwrap.dedent(
        f"""\
        sphinx-vite-builder: `{cmd_str}` exited with code {returncode} in {vite_root}.
        Vite reported a build error; the resulting wheel/docs would be
        unstyled. Aborting before any further build steps.

        Captured stderr:
        {textwrap.indent(stderr_block, "  ")}
        """,
    ).rstrip()


def _resolve_vite_root(project_root: pathlib.Path) -> pathlib.Path | None:
    """Locate the Vite project root next to ``project_root``.

    Convention: a sibling ``web/`` directory containing ``package.json``
    is the Vite project. Returns ``None`` if no such directory exists
    (e.g. when the build runs inside an unpacked sdist where ``web/``
    was excluded — in that case the caller should treat the static
    tree as pre-baked and skip vite).
    """
    candidate = project_root / "web"
    if candidate.is_dir() and (candidate / "package.json").is_file():
        return candidate
    return None


async def _run_install(
    vite_root: pathlib.Path,
    *,
    install_cmd: tuple[str, ...],
) -> None:
    """Run ``pnpm install --frozen-lockfile``; raise on non-zero exit."""
    proc = AsyncProcess(label="pnpm-install", logger=logger)
    await proc.start(install_cmd, cwd=vite_root)
    returncode = await proc.wait()
    if returncode != 0:
        raise NodeModulesInstallError(
            _format_install_failed_hint(
                vite_root=vite_root,
                install_cmd=install_cmd,
                returncode=returncode,
                stderr=proc.captured_stderr,
            ),
        )


async def _run_build(
    vite_root: pathlib.Path,
    *,
    build_cmd: tuple[str, ...],
) -> None:
    """Run ``pnpm exec vite build``; raise on non-zero exit."""
    proc = AsyncProcess(label="vite-build", logger=logger)
    await proc.start(build_cmd, cwd=vite_root)
    returncode = await proc.wait()
    if returncode != 0:
        raise ViteFailedError(
            _format_vite_failed_hint(
                vite_root=vite_root,
                build_cmd=build_cmd,
                returncode=returncode,
                stderr=proc.captured_stderr,
            ),
        )


def run_vite_build(
    project_root: pathlib.Path | None = None,
    *,
    package_manager: str = "pnpm",
) -> None:
    """Run a one-shot ``pnpm exec vite build`` in ``<project_root>/web``.

    Short-circuits when:

    - ``SPHINX_VITE_BUILDER_SKIP=1`` is set in the environment (escape
      hatch for downstream packagers who pre-bake the static tree
      themselves).
    - The expected ``web/`` directory is absent — the typical case
      when building a wheel from an unpacked sdist (where ``web/`` was
      excluded but ``static/`` was pre-baked into the sdist).

    Otherwise, fast-fails:

    - :class:`PnpmMissingError` if ``pnpm`` is not on ``PATH``.
    - :class:`NodeModulesInstallError` if ``pnpm install`` exits
      non-zero.
    - :class:`ViteFailedError` if ``pnpm exec vite build`` exits
      non-zero.
    """
    if os.environ.get("SPHINX_VITE_BUILDER_SKIP"):
        logger.info("SPHINX_VITE_BUILDER_SKIP set; skipping vite build")
        return

    project_root = (project_root or pathlib.Path.cwd()).resolve()
    vite_root = _resolve_vite_root(project_root)
    if vite_root is None:
        logger.info(
            "no web/ alongside %s; assuming pre-baked static tree (sdist build)",
            project_root,
        )
        return

    if shutil.which(package_manager) is None:
        raise PnpmMissingError(_format_pnpm_missing_hint(vite_root))

    install_cmd = pnpm_install_command(package_manager=package_manager)
    build_cmd = vite_build_command(package_manager=package_manager)
    needs_install = not (vite_root / "node_modules").is_dir()

    bus = AsyncioBus(name="sphinx-vite-builder-build-bus")
    bus.start()
    try:
        if needs_install:
            logger.info("installing JS deps in %s via %s", vite_root, install_cmd)
            bus.call_sync(_run_install(vite_root, install_cmd=install_cmd))
        logger.info("building vite assets in %s", vite_root)
        bus.call_sync(_run_build(vite_root, build_cmd=build_cmd))
    finally:
        bus.stop()


__all__: tuple[str, ...] = (
    "pnpm_install_command",
    "run_vite_build",
    "vite_build_command",
    "vite_watch_command",
)


# Re-exports for type-checker friendliness when consumers import
# the orchestration module directly.
_AsyncProcess: t.TypeAlias = AsyncProcess
_AsyncioBus: t.TypeAlias = AsyncioBus
