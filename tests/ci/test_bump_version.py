"""Tests for the workspace version-bump CLI."""

# bump-version: skip-file
# Version literals below describe bump scenarios ("bump FROM 0.0.1a7"),
# not live workspace state, so bump_version.py must leave them frozen.

from __future__ import annotations

import pathlib
import sys
import textwrap
import typing as t

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


class AltFormCase(t.NamedTuple):
    """Fixture for _alt_form() PEP 440 ↔ npm SemVer mapping."""

    test_id: str
    pep_version: str
    expected: str | None


_ALT_FORM_CASES: list[AltFormCase] = [
    AltFormCase(test_id="alpha", pep_version="0.0.1a16", expected="0.0.1-alpha.16"),
    AltFormCase(test_id="beta", pep_version="1.2.3b1", expected="1.2.3-beta.1"),
    AltFormCase(test_id="rc", pep_version="1.2.3rc4", expected="1.2.3-rc.4"),
    AltFormCase(test_id="stable", pep_version="1.2.3", expected=None),
    AltFormCase(test_id="garbage", pep_version="not-a-version", expected=None),
]


@pytest.mark.parametrize(
    list(AltFormCase._fields),
    _ALT_FORM_CASES,
    ids=[c.test_id for c in _ALT_FORM_CASES],
)
def test_alt_form(test_id: str, pep_version: str, expected: str | None) -> None:
    """_alt_form maps PEP 440 prereleases to npm SemVer; returns None otherwise."""
    assert bump_version._alt_form(pep_version) == expected


def test_bump_updates_astro_js_literals(tmp_path: pathlib.Path) -> None:
    """Bumping rewrites both PEP 440 and npm SemVer literals in one pass.

    The Python workspace stores its version in PEP 440 form (``0.0.1a7``);
    the astro JS stack stores the equivalent npm form (``0.0.1-alpha.7``)
    in ``package.json`` files alongside PEP 440 literals in ``.ts`` /
    ``.astro`` source. A single bump call must update both.
    """
    _seed_workspace(tmp_path, version="0.0.1a7")

    astro_root = tmp_path / "astro"
    workspace_root_pkg = astro_root / "package.json"
    workspace_root_pkg.parent.mkdir()
    workspace_root_pkg.write_text(
        '{"name":"astro-workspace","version":"0.0.1-alpha.7"}\n',
    )

    theme_dir = astro_root / "packages" / "theme"
    theme_src = theme_dir / "src"
    theme_src.mkdir(parents=True)
    (theme_dir / "package.json").write_text(
        '{"name":"@gp-sphinx/astro","version":"0.0.1-alpha.7"}\n',
    )
    (theme_src / "index.ts").write_text(
        "export const VERSION = '0.0.1a7'\n",
    )

    app_dir = astro_root / "apps" / "docs"
    app_components = app_dir / "src" / "components"
    app_components.mkdir(parents=True)
    (app_dir / "package.json").write_text(
        '{"name":"docs","version":"0.0.1-alpha.7"}\n',
    )
    (app_components / "TopNav.astro").write_text(
        "const VERSION = '0.0.1a7'\n",
    )

    changes = bump_version.bump_workspace_version("0.0.1a8", root=tmp_path)
    changed_paths = {path for path, _ in changes}

    assert workspace_root_pkg in changed_paths
    assert (theme_dir / "package.json") in changed_paths
    assert (theme_src / "index.ts") in changed_paths
    assert (app_dir / "package.json") in changed_paths
    assert (app_components / "TopNav.astro") in changed_paths

    assert '"version":"0.0.1-alpha.8"' in workspace_root_pkg.read_text()
    assert '"version":"0.0.1-alpha.8"' in (theme_dir / "package.json").read_text()
    assert "'0.0.1a8'" in (theme_src / "index.ts").read_text()
    assert '"version":"0.0.1-alpha.8"' in (app_dir / "package.json").read_text()
    assert "'0.0.1a8'" in (app_components / "TopNav.astro").read_text()


def test_bump_skips_node_modules(tmp_path: pathlib.Path) -> None:
    """Files under any node_modules/ directory are excluded even if they match.

    A vendored ``package.json`` inside ``node_modules`` could legitimately
    pin the same version literal as the workspace, but rewriting it would
    corrupt the dependency graph.
    """
    _seed_workspace(tmp_path, version="0.0.1a7")

    nm = tmp_path / "astro" / "packages" / "theme" / "node_modules" / "vendored"
    nm.mkdir(parents=True)
    (nm / "package.json").write_text(
        '{"name":"vendored","version":"0.0.1-alpha.7"}\n',
    )

    bump_version.bump_workspace_version("0.0.1a8", root=tmp_path)

    assert '"version":"0.0.1-alpha.7"' in (nm / "package.json").read_text()
