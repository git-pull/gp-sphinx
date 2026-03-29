"""Tests for CI package tooling."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts" / "ci"))
import package_tools


def test_workspace_version_is_lockstep() -> None:
    """All workspace packages share the same version."""
    assert package_tools.workspace_version() == "0.0.1a0"


def test_check_versions_passes_for_repo() -> None:
    """Current repository metadata satisfies the lockstep policy."""
    package_tools.check_versions()


def test_release_metadata_accepts_repo_tag() -> None:
    """Repo-wide release tags resolve to the shared version."""
    assert package_tools.release_metadata("v0.0.1a0") == {"version": "0.0.1a0"}


def test_release_metadata_rejects_package_tag() -> None:
    """Package-scoped tags are no longer valid release inputs."""
    with pytest.raises(SystemExit, match="invalid release tag format"):
        package_tools.release_metadata("gp-sphinx@v0.0.1a0")
