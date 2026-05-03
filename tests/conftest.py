"""Conftest.py (root-level) for gp-sphinx tests.

We keep this in root so pytest fixtures and doctest namespace fixtures are
available globally, and to avoid conftest.py from being included in the wheel.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

pytest_plugins = ("tests._snapshots",)


_GP_FURO_STATIC = (
    pathlib.Path(__file__).resolve().parents[1]
    / "packages"
    / "gp-furo-theme"
    / "src"
    / "gp_furo_theme"
    / "theme"
    / "gp-furo"
    / "static"
)
_REQUIRED_GP_FURO_ASSETS = ("scripts/furo.js", "styles/furo-tw.css")


def skip_if_gp_furo_assets_missing() -> None:
    """Skip the caller when vite-built gp-furo theme assets aren't on disk.

    The runtime fail-loud check in ``gp_furo_theme._builder_inited`` raises
    ``ConfigError`` when the static dir is missing. Integration tests that
    build a Sphinx project with ``html_theme = "gp-furo"`` (or
    ``sphinx-gp-theme``, which inherits from gp-furo) cannot run without
    those assets — call this from the fixture to skip cleanly rather than
    crashing the test session.
    """
    missing = [
        _GP_FURO_STATIC / asset
        for asset in _REQUIRED_GP_FURO_ASSETS
        if not (_GP_FURO_STATIC / asset).is_file()
    ]
    if missing:
        pytest.skip(
            f"gp-furo vite assets missing ({len(missing)} files). "
            "Run `just build-docs` from the workspace root, or "
            "`cd packages/gp-furo-theme/web && pnpm install --frozen-lockfile "
            "&& pnpm exec vite build`.",
        )


for src_path in sorted(
    (pathlib.Path(__file__).resolve().parents[1] / "packages").glob("*/src"),
):
    src_str = str(src_path)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


@pytest.fixture(scope="session")
def _doctest_tmp_path(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """Return a shared writable path for doctest examples."""
    return tmp_path_factory.mktemp("doctest")


@pytest.fixture(autouse=True)
def _doctest_namespace(
    doctest_namespace: dict[str, object],
    _doctest_tmp_path: pathlib.Path,
) -> None:
    """Inject common fixtures into doctest namespace."""
    doctest_namespace["tmp_path"] = _doctest_tmp_path
