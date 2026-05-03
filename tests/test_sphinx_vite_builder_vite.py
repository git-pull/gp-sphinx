"""Tests for the Vite/pnpm orchestration core.

Focused on the fast-fail discipline: missing pnpm, install failures,
vite build failures all surface as actionable diagnostic errors with
copy-pasteable hints.
"""

from __future__ import annotations

import pathlib
import shutil
import textwrap
import typing as t

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
# CI detection — pnpm-missing hint includes platform-specific setup recipes
# ---------------------------------------------------------------------------


def _clear_ci_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every CI-detection env var so detection starts from a clean slate."""
    for var in ("GITHUB_ACTIONS", "CIRCLECI", "TF_BUILD", "GITLAB_CI", "CI"):
        monkeypatch.delenv(var, raising=False)


def test_detect_ci_provider_returns_none_when_not_in_ci(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No truthy CI env var → no provider detected."""
    _clear_ci_env(monkeypatch)
    assert vite_module._detect_ci_provider() is None


class CIProviderCase(t.NamedTuple):
    """Test case for :func:`_detect_ci_provider`."""

    test_id: str
    env_var: str
    env_value: str
    expected: str | None


_CI_PROVIDER_FIXTURES: list[CIProviderCase] = [
    CIProviderCase(
        test_id="github-actions",
        env_var="GITHUB_ACTIONS",
        env_value="true",
        expected="github-actions",
    ),
    CIProviderCase(
        test_id="circleci",
        env_var="CIRCLECI",
        env_value="true",
        expected="circleci",
    ),
    CIProviderCase(
        test_id="azure-pipelines-mixed-case",
        # Azure sets TF_BUILD=True (capital T). Detection is case-insensitive.
        env_var="TF_BUILD",
        env_value="True",
        expected="azure-pipelines",
    ),
    CIProviderCase(
        test_id="gitlab",
        env_var="GITLAB_CI",
        env_value="true",
        expected="gitlab",
    ),
    CIProviderCase(
        test_id="generic-ci-fallback",
        env_var="CI",
        env_value="true",
        expected="ci",
    ),
    CIProviderCase(
        test_id="numeric-truthy",
        env_var="GITHUB_ACTIONS",
        env_value="1",
        expected="github-actions",
    ),
    CIProviderCase(
        test_id="explicit-false-skips",
        # Some platforms set the var to ``false`` rather than unsetting it.
        env_var="GITHUB_ACTIONS",
        env_value="false",
        expected=None,
    ),
]


@pytest.mark.parametrize(
    list(CIProviderCase._fields),
    _CI_PROVIDER_FIXTURES,
    ids=[c.test_id for c in _CI_PROVIDER_FIXTURES],
)
def test_detect_ci_provider(
    test_id: str,
    env_var: str,
    env_value: str,
    expected: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each canonical CI env var resolves to its provider name."""
    del test_id  # Used by pytest IDs.
    _clear_ci_env(monkeypatch)
    monkeypatch.setenv(env_var, env_value)
    assert vite_module._detect_ci_provider() == expected


def test_detect_ci_provider_specific_beats_generic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When both GITHUB_ACTIONS and CI are truthy, specific wins.

    GitHub Actions sets both ``GITHUB_ACTIONS=true`` AND ``CI=true``;
    detection MUST surface the specific provider so the recipe block
    is GitHub-flavoured rather than the generic fallback.
    """
    _clear_ci_env(monkeypatch)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("CI", "true")
    assert vite_module._detect_ci_provider() == "github-actions"


def test_pnpm_missing_hint_omits_ci_block_outside_ci(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local-dev failure → no CI recipe section."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)
    _clear_ci_env(monkeypatch)
    project = _make_vite_project(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    with pytest.raises(PnpmMissingError) as exc_info:
        run_vite_build(project)
    msg = str(exc_info.value)
    assert "Detected CI provider" not in msg
    assert "Add the following to your pipeline" not in msg


def test_pnpm_missing_hint_includes_github_actions_recipe(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub Actions failure → hint includes pnpm/action-setup snippet."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)
    _clear_ci_env(monkeypatch)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    project = _make_vite_project(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    with pytest.raises(PnpmMissingError) as exc_info:
        run_vite_build(project)
    msg = str(exc_info.value)
    assert "Detected CI provider: GitHub Actions" in msg
    assert "pnpm/action-setup@v6" in msg
    assert "actions/setup-node@v6" in msg


def test_pnpm_missing_hint_includes_circleci_recipe(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CircleCI failure → hint includes corepack-based pnpm install snippet."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)
    _clear_ci_env(monkeypatch)
    monkeypatch.setenv("CIRCLECI", "true")
    project = _make_vite_project(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    with pytest.raises(PnpmMissingError) as exc_info:
        run_vite_build(project)
    msg = str(exc_info.value)
    assert "Detected CI provider: CircleCI" in msg
    assert "corepack enable" in msg
    assert "corepack prepare pnpm" in msg


def test_pnpm_missing_hint_includes_azure_pipelines_recipe(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Azure Pipelines failure → hint includes NodeTool@0 + corepack snippet."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)
    _clear_ci_env(monkeypatch)
    monkeypatch.setenv("TF_BUILD", "True")
    project = _make_vite_project(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    with pytest.raises(PnpmMissingError) as exc_info:
        run_vite_build(project)
    msg = str(exc_info.value)
    assert "Detected CI provider: Azure Pipelines" in msg
    assert "NodeTool@0" in msg
    assert "corepack enable" in msg


def test_pnpm_missing_hint_includes_gitlab_recipe(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitLab CI failure → hint includes before_script corepack snippet."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)
    _clear_ci_env(monkeypatch)
    monkeypatch.setenv("GITLAB_CI", "true")
    project = _make_vite_project(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    with pytest.raises(PnpmMissingError) as exc_info:
        run_vite_build(project)
    msg = str(exc_info.value)
    assert "Detected CI provider: GitLab CI" in msg
    assert "before_script:" in msg
    assert "corepack prepare pnpm" in msg


def test_pnpm_missing_hint_generic_ci_fallback(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unrecognised CI (only ``CI=true``) → generic fallback message."""
    monkeypatch.delenv("SPHINX_VITE_BUILDER_SKIP", raising=False)
    _clear_ci_env(monkeypatch)
    monkeypatch.setenv("CI", "true")
    project = _make_vite_project(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    with pytest.raises(PnpmMissingError) as exc_info:
        run_vite_build(project)
    msg = str(exc_info.value)
    assert "Detected CI provider: this CI environment" in msg
    assert "Use your CI's package-manager setup mechanism" in msg


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
