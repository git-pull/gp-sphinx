"""Tests for the ``{surface-changelog}`` showcase directive."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "docs" / "_ext"))

import package_reference


def test_current_surface_keys_includes_directive_role_and_config_kinds() -> None:
    """The flat key set distinguishes ``directive:`` / ``role:`` / ``config:``."""
    record = next(
        r
        for r in package_reference.workspace_package_records()
        if r.name == "sphinx-autodoc-argparse"
    )
    keys = package_reference._current_surface_keys(record)
    assert any(k.startswith("directive:") for k in keys)
    # argparse registers at least one directive
    assert "directive:argparse" in keys


def test_surface_changelog_markdown_warns_when_no_snapshot_exists(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A package with no snapshot file gets the no-prior-snapshot notice.

    Body-only output: the directive emits the comparison body; the
    stub at ``packages/<name>/surface-diff.md`` provides anchor + H1.
    """
    monkeypatch.setattr(
        package_reference,
        "_surface_snapshot_path",
        lambda name: tmp_path / f"{name}-no-such-file.json",
    )
    rendered = package_reference._surface_changelog_markdown("sphinx-fonts")
    # No anchor or H1 emitted by the directive
    assert "(sphinx-fonts-surface-diff)=" not in rendered
    assert "# Surface diff" not in rendered
    assert "No prior snapshot recorded" in rendered


def test_surface_changelog_markdown_renders_added_section(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the snapshot is empty, every current surface key shows under Added."""
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps([]), encoding="utf-8")
    monkeypatch.setattr(
        package_reference,
        "_surface_snapshot_path",
        lambda _name: snapshot,
    )
    rendered = package_reference._surface_changelog_markdown("sphinx-autodoc-argparse")
    assert "## Added" in rendered
    assert "directive:argparse" in rendered
    assert "## Removed" not in rendered  # no removals against empty snapshot


def test_surface_changelog_markdown_renders_removed_when_snapshot_has_extras(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Snapshot keys not in the current surface show under Removed."""
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps(["directive:argparse", "directive:never-existed"]),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        package_reference,
        "_surface_snapshot_path",
        lambda _name: snapshot,
    )
    rendered = package_reference._surface_changelog_markdown("sphinx-autodoc-argparse")
    assert "## Removed" in rendered
    assert "directive:never-existed" in rendered
    assert "## Unchanged" in rendered  # argparse stayed


def test_surface_changelog_markdown_returns_empty_for_unknown_package() -> None:
    """Unknown package returns the empty string."""
    rendered = package_reference._surface_changelog_markdown("definitely-no-such-pkg")
    assert rendered == ""
