"""Tests for the workspace version-bump CLI."""

# bump-version: skip-file
# Version literals below describe bump scenarios ("bump FROM 0.0.1a7"),
# not live workspace state, so bump_version.py must leave them frozen.

from __future__ import annotations

import pathlib
import sys
import textwrap

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "ci"))
import bump_version


def _seed_workspace(tmp_path: pathlib.Path, version: str = "0.0.1a7") -> None:
    """Populate a minimal workspace tree for bump tests."""
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(f"""
            [project]
            name = "demo-workspace"
            version = "{version}"
        """).lstrip(),
    )
    pkg = tmp_path / "packages" / "demo" / "src" / "demo"
    pkg.mkdir(parents=True)
    (pkg.parent.parent / "pyproject.toml").write_text(
        textwrap.dedent(f"""
            [project]
            name = "demo"
            version = "{version}"
        """).lstrip(),
    )
    (pkg / "__init__.py").write_text(f'__version__ = "{version}"\n')
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_demo.py").write_text(
        f'EXPECTED = "{version}"\n',
    )
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "helper.py").write_text(
        f'DEFAULT = "{version}"\n',
    )


def test_bump_updates_pyproject_and_source(tmp_path: pathlib.Path) -> None:
    """Bumping rewrites pyproject.toml, package source, tests, and scripts."""
    _seed_workspace(tmp_path, version="0.0.1a7")
    changes = bump_version.bump_workspace_version("0.0.1a8", root=tmp_path)

    changed_names = {path.name for path, _ in changes}
    assert "pyproject.toml" in changed_names
    assert "__init__.py" in changed_names
    assert "test_demo.py" in changed_names
    assert "helper.py" in changed_names

    pkg_init = tmp_path / "packages" / "demo" / "src" / "demo" / "__init__.py"
    assert pkg_init.read_text() == '__version__ = "0.0.1a8"\n'
    assert '"0.0.1a8"' in (tmp_path / "pyproject.toml").read_text()


def test_bump_skips_files_without_old_version(tmp_path: pathlib.Path) -> None:
    """Files that do not mention the old version are not rewritten."""
    _seed_workspace(tmp_path, version="0.0.1a7")
    unrelated = tmp_path / "tests" / "test_unrelated.py"
    unrelated.write_text('UNRELATED = "something-else"\n')

    changes = bump_version.bump_workspace_version("0.0.1a8", root=tmp_path)
    assert unrelated.read_text() == 'UNRELATED = "something-else"\n'
    assert all(path != unrelated for path, _ in changes)


def test_bump_skips_files_with_sentinel_marker(tmp_path: pathlib.Path) -> None:
    """Files carrying the skip-file sentinel comment are left untouched."""
    _seed_workspace(tmp_path, version="0.0.1a7")
    frozen = tmp_path / "tests" / "test_frozen.py"
    frozen_contents = textwrap.dedent(
        """\
        # bump-version: skip-file
        SCENARIO_OLD = "0.0.1a7"
        SCENARIO_NEW = "0.0.1a8"
        """,
    )
    frozen.write_text(frozen_contents)

    changes = bump_version.bump_workspace_version("0.0.1a8", root=tmp_path)

    assert frozen.read_text() == frozen_contents
    assert all(path != frozen for path, _ in changes)


def test_bump_rejects_same_version(tmp_path: pathlib.Path) -> None:
    """Bumping to the current version is rejected loudly."""
    _seed_workspace(tmp_path, version="0.0.1a7")
    with pytest.raises(SystemExit, match="equals current version"):
        bump_version.bump_workspace_version("0.0.1a7", root=tmp_path)


def test_bump_rejects_invalid_pep440(tmp_path: pathlib.Path) -> None:
    """Non-PEP-440 version strings are rejected."""
    _seed_workspace(tmp_path, version="0.0.1a7")
    with pytest.raises(SystemExit, match="invalid PEP 440 version"):
        bump_version.bump_workspace_version("not-a-version!!", root=tmp_path)


def test_bump_main_prints_summary(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI entry point prints the old -> new header and per-file lines."""
    _seed_workspace(tmp_path, version="0.0.1a7")
    monkeypatch.setattr(bump_version, "_workspace_root", lambda: tmp_path)

    exit_code = bump_version.main(["0.0.1a8"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "0.0.1a7 -> 0.0.1a8" in out
    assert "file(s) changed" in out
