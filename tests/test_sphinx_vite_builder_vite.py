"""Tests for the Vite/pnpm orchestration core.

Focused on the fast-fail discipline: missing pnpm, install failures,
vite build failures all surface as actionable diagnostic errors with
copy-pasteable hints.
"""

from __future__ import annotations

import pathlib
import shutil
import textwrap

import pytest
from sphinx_vite_builder._internal import vite as vite_module
from sphinx_vite_builder._internal.errors import (
    NodeModulesInstallError,
    PnpmMissingError,
    SphinxViteBuilderError,
    ViteFailedError,
)
from sphinx_vite_builder._internal.vite import (
    pnpm_install_command,
    run_vite_build,
    vite_build_command,
    vite_watch_command,
)

# ---------------------------------------------------------------------------
# Command helpers — simple argv builders with stable ordering
# ---------------------------------------------------------------------------


def test_pnpm_install_command_default() -> None:
    """``pnpm install --frozen-lockfile`` is the canonical invocation."""
    assert pnpm_install_command() == ("pnpm", "install", "--frozen-lockfile")


def test_pnpm_install_command_alternate_manager() -> None:
    """The package manager is parameterized for npm/yarn coexistence."""
    assert pnpm_install_command(package_manager="npm") == (
        "npm",
        "install",
        "--frozen-lockfile",
    )


def test_vite_build_command_default() -> None:
    """One-shot vite build uses ``exec`` (no shell wrapper)."""
    assert vite_build_command() == ("pnpm", "exec", "vite", "build")


def test_vite_watch_command_default() -> None:
    """Watch mode appends ``--watch`` so vite stays resident."""
    assert vite_watch_command() == ("pnpm", "exec", "vite", "build", "--watch")


# ---------------------------------------------------------------------------
# Short-circuit paths — no vite invocation expected
# ---------------------------------------------------------------------------


def test_run_vite_build_short_circuits_when_skip_env_set(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``SPHINX_VITE_BUILDER_SKIP=1`` is the escape hatch for downstream packagers."""
    monkeypatch.setenv("SPHINX_VITE_BUILDER_SKIP", "1")

    def _fail_lookup(_name: str) -> str | None:
        msg = "shutil.which should not be called when SKIP is set"
        raise AssertionError(msg)

    monkeypatch.setattr(shutil, "which", _fail_lookup)
    # No web/ — but we don't even get that far when SKIP is set.
    run_vite_build(tmp_path)


def test_run_vite_build_short_circuits_when_web_dir_absent(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unpacked-sdist case: no web/ alongside, vite is a no-op."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)

    def _fail_lookup(_name: str) -> str | None:
        msg = "shutil.which should not be called when web/ is absent"
        raise AssertionError(msg)

    monkeypatch.setattr(shutil, "which", _fail_lookup)
    # tmp_path has no web/ subdirectory.
    run_vite_build(tmp_path)


def test_run_vite_build_short_circuits_when_web_lacks_package_json(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``web/`` without ``package.json`` is treated as not-a-vite-project."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)
    (tmp_path / "web").mkdir()  # no package.json inside

    def _fail_lookup(_name: str) -> str | None:
        msg = "shutil.which should not be called when web/ lacks package.json"
        raise AssertionError(msg)

    monkeypatch.setattr(shutil, "which", _fail_lookup)
    run_vite_build(tmp_path)


# ---------------------------------------------------------------------------
# Fast-fail: pnpm not on PATH
# ---------------------------------------------------------------------------


def _make_vite_project(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a minimal ``web/`` directory layout so detection fires."""
    web = tmp_path / "web"
    web.mkdir()
    (web / "package.json").write_text('{"name": "test-vite-project"}\n')
    return tmp_path


def test_run_vite_build_raises_pnpm_missing_with_actionable_hint(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``pnpm`` not on PATH → ``PnpmMissingError`` with corepack/install hints."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)
    project = _make_vite_project(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    with pytest.raises(PnpmMissingError) as exc_info:
        run_vite_build(project)

    msg = str(exc_info.value)
    assert "pnpm" in msg
    assert "corepack enable" in msg
    assert "https://pnpm.io/installation" in msg
    assert "SPHINX_VITE_BUILDER_SKIP" in msg


def test_pnpm_missing_error_inherits_from_base() -> None:
    """Diagnostic errors share a single base for easy ``except`` clauses."""
    assert issubclass(PnpmMissingError, SphinxViteBuilderError)
    assert issubclass(NodeModulesInstallError, SphinxViteBuilderError)
    assert issubclass(ViteFailedError, SphinxViteBuilderError)


# ---------------------------------------------------------------------------
# Fast-fail: pnpm install / vite build non-zero exit
#
# We patch the orchestration's awaitable run_install / run_build helpers
# rather than spawning real pnpm — keeps tests fast and deterministic.
# ---------------------------------------------------------------------------


def test_run_vite_build_raises_install_error_when_install_fails(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``pnpm install`` non-zero → ``NodeModulesInstallError`` with rerun recipe."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)
    project = _make_vite_project(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: "/fake/pnpm")
    # Force the install branch by ensuring node_modules is absent.
    assert not (project / "web" / "node_modules").exists()

    async def _fake_install(*_args: object, **_kwargs: object) -> None:
        msg = textwrap.dedent(
            """\
            sphinx-vite-builder: `pnpm install --frozen-lockfile` exited with code 7
            Captured stderr:
              fake stderr from pnpm
            """,
        ).rstrip()
        raise NodeModulesInstallError(msg)

    monkeypatch.setattr(vite_module, "_run_install", _fake_install)

    with pytest.raises(NodeModulesInstallError) as exc_info:
        run_vite_build(project)
    assert "exited with code 7" in str(exc_info.value)
    assert "fake stderr from pnpm" in str(exc_info.value)


def test_run_vite_build_raises_vite_error_when_build_fails(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``pnpm exec vite build`` non-zero → ``ViteFailedError`` with stderr."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)
    project = _make_vite_project(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: "/fake/pnpm")
    # Pre-create node_modules so the install branch is skipped.
    (project / "web" / "node_modules").mkdir()

    async def _fake_build(*_args: object, **_kwargs: object) -> None:
        msg = textwrap.dedent(
            """\
            sphinx-vite-builder: `pnpm exec vite build` exited with code 1
            Captured stderr:
              ESM resolve failed: missing dependency
            """,
        ).rstrip()
        raise ViteFailedError(msg)

    monkeypatch.setattr(vite_module, "_run_build", _fake_build)

    with pytest.raises(ViteFailedError) as exc_info:
        run_vite_build(project)
    assert "exited with code 1" in str(exc_info.value)
    assert "ESM resolve failed" in str(exc_info.value)


def test_run_vite_build_skips_install_when_node_modules_exists(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A populated ``node_modules/`` short-circuits the install step."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)
    project = _make_vite_project(tmp_path)
    (project / "web" / "node_modules").mkdir()
    monkeypatch.setattr(shutil, "which", lambda _name: "/fake/pnpm")

    install_calls = 0
    build_calls = 0

    async def _fake_install(*_args: object, **_kwargs: object) -> None:
        nonlocal install_calls
        install_calls += 1

    async def _fake_build(*_args: object, **_kwargs: object) -> None:
        nonlocal build_calls
        build_calls += 1

    monkeypatch.setattr(vite_module, "_run_install", _fake_install)
    monkeypatch.setattr(vite_module, "_run_build", _fake_build)

    run_vite_build(project)
    assert install_calls == 0
    assert build_calls == 1


def test_run_vite_build_runs_install_when_node_modules_missing(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing ``node_modules/`` triggers ``pnpm install`` before build."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)
    project = _make_vite_project(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: "/fake/pnpm")

    order: list[str] = []

    async def _fake_install(*_args: object, **_kwargs: object) -> None:
        order.append("install")

    async def _fake_build(*_args: object, **_kwargs: object) -> None:
        order.append("build")

    monkeypatch.setattr(vite_module, "_run_install", _fake_install)
    monkeypatch.setattr(vite_module, "_run_build", _fake_build)

    run_vite_build(project)
    assert order == ["install", "build"]
