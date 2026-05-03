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


def _detect_ci_provider() -> str | None:
    """Return a canonical CI-provider name, or ``None`` if not in CI.

    Detection precedence: most-specific provider wins. Each provider's
    canonical env var (per their docs) is checked first; the generic
    ``CI=true`` is the fallback for "we know we're in CI but don't
    recognise the provider".

    Provider env vars (canonical, per upstream docs):

    - GitHub Actions: ``GITHUB_ACTIONS=true``
    - CircleCI: ``CIRCLECI=true``
    - Azure Pipelines: ``TF_BUILD=True`` (Team Foundation Build)
    - GitLab CI: ``GITLAB_CI=true``
    - Generic: ``CI=true``
    """
    env = os.environ
    # Map of "canonical name" → "env var to check (truthy)". Order
    # matters: more-specific entries first.
    providers: tuple[tuple[str, str], ...] = (
        ("github-actions", "GITHUB_ACTIONS"),
        ("circleci", "CIRCLECI"),
        ("azure-pipelines", "TF_BUILD"),
        ("gitlab", "GITLAB_CI"),
        ("ci", "CI"),
    )
    for name, var in providers:
        value = env.get(var, "").strip().lower()
        if value in {"1", "true"}:
            return name
    return None


# Each per-provider snippet is a *copy-pasteable* config fragment that
# adds pnpm + Node to the platform's pipeline before the Python build
# step runs. Versions follow the upstream pnpm CI guide
# (https://pnpm.io/continuous-integration); update in lockstep with
# the workspace's pnpm-lock.yaml's `packageManager` if it pins
# something different.
_CI_SETUP_RECIPES: dict[str, str] = {
    "github-actions": textwrap.dedent(
        """\
        - uses: pnpm/action-setup@v6
          with:
            version: 10
        - uses: actions/setup-node@v6
          with:
            node-version: 22
            cache: pnpm""",
    ),
    "circleci": textwrap.dedent(
        """\
        - run:
            name: Set up pnpm
            command: |
              npm install --global corepack@latest
              corepack enable
              corepack prepare pnpm@latest-10 --activate""",
    ),
    "azure-pipelines": textwrap.dedent(
        """\
        - task: NodeTool@0
          inputs:
            versionSpec: '22.x'
          displayName: 'Set up Node'
        - script: |
            npm install --global corepack@latest
            corepack enable
            corepack prepare pnpm@latest-10 --activate
          displayName: 'Set up pnpm'""",
    ),
    "gitlab": textwrap.dedent(
        """\
        before_script:
          - npm install --global corepack@latest
          - corepack enable
          - corepack prepare pnpm@latest-10 --activate""",
    ),
    "ci": "  # Use your CI's package-manager setup mechanism to install pnpm",
}


def _format_ci_recipe_block(provider: str | None) -> str:
    """Return a multi-line CI-specific setup snippet, or an empty string.

    Called by :func:`_format_pnpm_missing_hint` when CI is detected so
    the user's error message includes a copy-pasteable config fragment
    for their platform.
    """
    if provider is None:
        return ""

    pretty: dict[str, str] = {
        "github-actions": "GitHub Actions",
        "circleci": "CircleCI",
        "azure-pipelines": "Azure Pipelines",
        "gitlab": "GitLab CI",
        "ci": "this CI environment",
    }
    label = pretty.get(provider, provider)
    recipe = _CI_SETUP_RECIPES.get(provider, "")
    return textwrap.dedent(
        f"""\

        Detected CI provider: {label}. Add the following to your pipeline
        config (before the Python build step that triggers this backend):

{textwrap.indent(recipe, "          ")}
        """,
    ).rstrip()


def _format_pnpm_missing_hint(vite_root: pathlib.Path) -> str:
    """Multi-line, copy-pasteable hint when pnpm is not on PATH."""
    ci_recipe = _format_ci_recipe_block(_detect_ci_provider())
    return (
        textwrap.dedent(
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
        + ci_recipe
    )


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
