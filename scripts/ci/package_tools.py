"""Workspace package tooling for CI and release automation."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap
import typing as t
from dataclasses import dataclass

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


@dataclass(frozen=True)
class WorkspacePackage:
    """Metadata for a publishable workspace package.

    Parameters
    ----------
    name : str
        Distribution name from ``pyproject.toml``.
    version : str
        Package version from ``pyproject.toml``.
    path : pathlib.Path
        Directory containing the package ``pyproject.toml``.
    module_name : str
        Importable top-level module name from the package ``src`` layout.
    """

    name: str
    version: str
    path: pathlib.Path
    module_name: str


def _workspace_root() -> pathlib.Path:
    """Return the repository root."""
    return pathlib.Path(__file__).resolve().parents[2]


def _load_toml(path: pathlib.Path) -> dict[str, t.Any]:
    """Load a TOML file.

    Parameters
    ----------
    path : pathlib.Path
        TOML file to load.

    Returns
    -------
    dict[str, Any]
        Parsed TOML data.
    """
    with path.open("rb") as handle:
        return t.cast(dict[str, t.Any], tomllib.load(handle))


def _root_project(root: pathlib.Path) -> dict[str, t.Any]:
    """Return the root project table from ``pyproject.toml``."""
    return t.cast(dict[str, t.Any], _load_toml(root / "pyproject.toml")["project"])


def workspace_packages(root: pathlib.Path | None = None) -> dict[str, WorkspacePackage]:
    """Return publishable workspace packages keyed by distribution name.

    Parameters
    ----------
    root : pathlib.Path | None
        Repository root. Defaults to the current workspace root.

    Returns
    -------
    dict[str, WorkspacePackage]
        Mapping of distribution name to package metadata.
    """
    workspace_root = root or _workspace_root()
    packages: dict[str, WorkspacePackage] = {}
    for pyproject_path in sorted(
        (workspace_root / "packages").glob("*/pyproject.toml")
    ):
        data = _load_toml(pyproject_path)
        project = data["project"]
        src_dir = pyproject_path.parent / "src"
        module_dir = next(
            (path for path in src_dir.iterdir() if path.is_dir()),
            None,
        )
        if module_dir is None:
            msg = f"No module directory found in {src_dir}"
            raise ValueError(msg)
        package = WorkspacePackage(
            name=project["name"],
            version=project["version"],
            path=pyproject_path.parent,
            module_name=module_dir.name,
        )
        packages[package.name] = package
    return packages


def _dependency_entries(project: dict[str, t.Any]) -> list[tuple[str, str]]:
    """Return flattened dependency entries for a project table."""
    project_name = t.cast(str, project["name"])
    dependencies = [
        (project_name, dependency)
        for dependency in t.cast(list[str], project.get("dependencies", []))
    ]
    optional = t.cast(dict[str, list[str]], project.get("optional-dependencies", {}))
    entries = list(dependencies)
    for group, group_dependencies in optional.items():
        owner = f"{project_name}[{group}]"
        entries.extend((owner, dependency) for dependency in group_dependencies)
    return entries


def _base_requirement(requirement: str) -> str:
    """Strip environment markers from a dependency specification."""
    return requirement.split(";", 1)[0].strip()


def _is_workspace_dependency(requirement: str, package_name: str) -> bool:
    """Return whether a requirement references a workspace package."""
    base = _base_requirement(requirement)
    pattern = (
        rf"{re.escape(package_name)}(?:\[[^]]+\])?(?:\s*(?:==|>=|<=|~=|!=|<|>).*)?"
    )
    return re.fullmatch(pattern, base) is not None


def _is_exact_workspace_pin(requirement: str, package_name: str, version: str) -> bool:
    """Return whether a requirement pins a workspace package to one version."""
    base = _base_requirement(requirement)
    pattern = rf"{re.escape(package_name)}(?:\[[^]]+\])?\s*==\s*{re.escape(version)}"
    return re.fullmatch(pattern, base) is not None


def workspace_version(root: pathlib.Path | None = None) -> str:
    """Return the shared workspace version.

    Parameters
    ----------
    root : pathlib.Path | None
        Repository root. Defaults to the current workspace root.

    Returns
    -------
    str
        Shared version used by the root package and all publishable packages.
    """
    workspace_root = root or _workspace_root()
    packages = workspace_packages(workspace_root)
    versions = sorted({package.version for package in packages.values()})
    if len(versions) != 1:
        details = ", ".join(
            f"{package.name}={package.version}" for package in packages.values()
        )
        message = f"workspace package versions differ: {details}"
        raise SystemExit(message)

    version = versions[0]
    root_version = t.cast(str, _root_project(workspace_root)["version"])
    if root_version != version:
        message = (
            f"root workspace version {root_version} does not match "
            f"publishable package version {version}"
        )
        raise SystemExit(message)
    return version


def _run(
    args: list[str],
    *,
    cwd: pathlib.Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and raise on failure.

    Parameters
    ----------
    args : list[str]
        Command and arguments.
    cwd : pathlib.Path | None
        Working directory.
    env : dict[str, str] | None
        Extra environment variables.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Completed subprocess object.
    """
    cmd_env = os.environ.copy()
    if env:
        cmd_env.update(env)
    try:
        return subprocess.run(
            args,
            check=True,
            cwd=str(cwd) if cwd else None,
            env=cmd_env,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            sys.stdout.write(exc.stdout)
        if exc.stderr:
            sys.stderr.write(exc.stderr)
        raise


def _create_venv(tmpdir: pathlib.Path) -> pathlib.Path:
    """Create a temporary virtual environment and return its Python path."""
    venv_dir = tmpdir / "venv"
    _run(["uv", "venv", str(venv_dir)])
    return venv_dir / "bin" / "python"


def _install_into_venv(
    python_path: pathlib.Path,
    *requirements: str,
    find_links: pathlib.Path | None = None,
) -> None:
    """Install requirements into a temporary virtual environment."""
    cmd = ["uv", "pip", "install", "--python", str(python_path)]
    if find_links is not None:
        cmd.extend(["--find-links", str(find_links)])
    cmd.extend(requirements)
    _run(cmd)


def _workspace_wheel_requirements(dist_dir: pathlib.Path) -> list[str]:
    """Return explicit local wheel paths for built workspace packages."""
    return sorted(str(path) for path in dist_dir.glob("*.whl"))


def _run_python(python_path: pathlib.Path, source: str) -> None:
    """Run inline Python code with the given interpreter."""
    _run([str(python_path), "-c", source])


def _run_sphinx_build(
    python_path: pathlib.Path,
    source_dir: pathlib.Path,
    build_dir: pathlib.Path,
) -> None:
    """Run ``sphinx-build`` with warnings treated as errors."""
    _run(
        [
            str(python_path.parent / "sphinx-build"),
            "-W",
            "-b",
            "html",
            str(source_dir),
            str(build_dir),
        ],
    )


def check_versions(root: pathlib.Path | None = None) -> None:
    """Validate lockstep versions, first-party pins, and runtime metadata.

    Parameters
    ----------
    root : pathlib.Path | None
        Repository root. Defaults to the current workspace root.
    """
    workspace_root = root or _workspace_root()
    packages = workspace_packages(workspace_root)
    mismatches: list[str] = []

    package_versions = {package.name: package.version for package in packages.values()}
    unique_versions = sorted(set(package_versions.values()))
    shared_version: str | None = None
    if len(unique_versions) != 1:
        details = ", ".join(
            f"{name}={version}" for name, version in sorted(package_versions.items())
        )
        mismatches.append(f"workspace package versions differ: {details}")
    else:
        shared_version = unique_versions[0]

    root_project = _root_project(workspace_root)
    root_version = t.cast(str, root_project["version"])
    if shared_version is not None and root_version != shared_version:
        mismatches.append(
            f"gp-sphinx-workspace: pyproject={root_version}, workspace={shared_version}"
        )

    if shared_version is not None:
        package_names = set(packages)
        projects_to_check = [root_project] + [
            _load_toml(package.path / "pyproject.toml")["project"]
            for package in packages.values()
        ]
        for project in projects_to_check:
            for owner, dependency in _dependency_entries(project):
                for package_name in sorted(package_names):
                    if not _is_workspace_dependency(dependency, package_name):
                        continue
                    if not _is_exact_workspace_pin(
                        dependency,
                        package_name,
                        shared_version,
                    ):
                        mismatches.append(
                            f"{owner}: first-party dependency must pin "
                            f"{package_name}=={shared_version} (got {dependency})"
                        )

    for package in packages.values():
        sys.path.insert(0, str(package.path / "src"))
        try:
            module = importlib.import_module(package.module_name)
        finally:
            sys.path.pop(0)

        runtime_version = getattr(module, "__version__", None)
        if runtime_version is not None and runtime_version != package.version:
            mismatches.append(
                f"{package.name}: pyproject={package.version}, "
                f"runtime={runtime_version}"
            )

    if mismatches:
        joined = "\n".join(mismatches)
        message = f"version mismatch detected:\n{joined}"
        raise SystemExit(message)


def release_metadata(tag: str, root: pathlib.Path | None = None) -> dict[str, str]:
    """Parse and validate a lockstep release tag.

    Parameters
    ----------
    tag : str
        Git tag in ``vX.Y.Z`` format.
    root : pathlib.Path | None
        Repository root.

    Returns
    -------
    dict[str, str]
        Shared workspace version for the release.
    """
    match = re.fullmatch(r"v(?P<version>.+)", tag)
    if match is None:
        message = f"invalid release tag format: {tag}"
        raise SystemExit(message)

    version = match.group("version")
    shared_version = workspace_version(root)
    if version != shared_version:
        message = (
            f"tag version {version} does not match shared workspace version "
            f"{shared_version}"
        )
        raise SystemExit(message)

    return {"version": shared_version}


def smoke_root_install(root: pathlib.Path | None = None) -> None:
    """Verify that installing the repo root exposes the expected imports."""
    workspace_root = root or _workspace_root()
    with tempfile.TemporaryDirectory() as tmp:
        python_path = _create_venv(pathlib.Path(tmp))
        _install_into_venv(python_path, str(workspace_root))
        _run_python(
            python_path,
            (
                "import gp_sphinx; import gp_sphinx_workspace; "
                "print(gp_sphinx.__version__); print(gp_sphinx_workspace.__file__)"
            ),
        )


def smoke_gp_sphinx(dist_dir: pathlib.Path, version: str) -> None:
    """Build a minimal Sphinx project using ``merge_sphinx_config()``."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = pathlib.Path(tmp)
        docs_dir = tmpdir / "docs"
        docs_dir.mkdir()
        # Create the standard project directories that merge_sphinx_config() expects
        (docs_dir / "_static").mkdir()
        (docs_dir / "_templates").mkdir()
        (docs_dir / "conf.py").write_text(
            textwrap.dedent(
                """
                from gp_sphinx.config import merge_sphinx_config

                conf = merge_sphinx_config(
                    project="demo",
                    version="0.0.1a0",
                    copyright="2026",
                )
                globals().update(conf)
                """,
            ).lstrip(),
        )
        (docs_dir / "index.rst").write_text("Demo\n====\n")

        python_path = _create_venv(tmpdir)
        _install_into_venv(
            python_path,
            *_workspace_wheel_requirements(dist_dir),
        )
        _run_sphinx_build(python_path, docs_dir, tmpdir / "_build")


def smoke_sphinx_gptheme(dist_dir: pathlib.Path, version: str) -> None:
    """Build a minimal Sphinx project using the standalone theme."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = pathlib.Path(tmp)
        docs_dir = tmpdir / "docs"
        docs_dir.mkdir()
        (docs_dir / "conf.py").write_text("html_theme = 'sphinx-gptheme'\n")
        (docs_dir / "index.rst").write_text("Demo\n====\n")

        python_path = _create_venv(tmpdir)
        _install_into_venv(
            python_path,
            *_workspace_wheel_requirements(dist_dir),
        )
        _run_sphinx_build(python_path, docs_dir, tmpdir / "_build")

        html = (tmpdir / "_build" / "index.html").read_text()
        for stylesheet in ("custom.css", "argparse-highlight.css"):
            if stylesheet not in html:
                message = f"missing bundled stylesheet reference: {stylesheet}"
                raise SystemExit(message)


def smoke_sphinx_fonts(dist_dir: pathlib.Path, version: str) -> None:
    """Verify the standalone extension installs and imports cleanly."""
    with tempfile.TemporaryDirectory() as tmp:
        python_path = _create_venv(pathlib.Path(tmp))
        _install_into_venv(
            python_path,
            *_workspace_wheel_requirements(dist_dir),
        )
        _run_python(
            python_path,
            (
                "import sphinx_fonts; from sphinx_fonts import _cache_dir, setup; "
                f"assert sphinx_fonts.__version__ == {version!r}; "
                "assert _cache_dir().name == 'sphinx-fonts'; "
                "assert callable(setup)"
            ),
        )


def smoke_sphinx_argparse_neo(dist_dir: pathlib.Path, version: str) -> None:
    """Verify the argparse extension installs and imports cleanly."""
    with tempfile.TemporaryDirectory() as tmp:
        python_path = _create_venv(pathlib.Path(tmp))
        _install_into_venv(
            python_path,
            *_workspace_wheel_requirements(dist_dir),
        )
        _run_python(
            python_path,
            (
                "import sphinx_argparse_neo; "
                "from sphinx_argparse_neo import ArgparseDirective; "
                f"assert sphinx_argparse_neo.__version__ == {version!r}; "
                "assert ArgparseDirective is not None"
            ),
        )


def smoke(
    target: str,
    *,
    dist_dir: pathlib.Path | None = None,
    root: pathlib.Path | None = None,
) -> None:
    """Run a named smoke scenario."""
    workspace_root = root or _workspace_root()
    packages = workspace_packages(workspace_root)
    if target == "root-install":
        smoke_root_install(workspace_root)
        return
    if dist_dir is None:
        message = "--dist-dir is required for package smoke tests"
        raise SystemExit(message)

    runners: dict[str, t.Callable[[pathlib.Path, str], None]] = {
        "gp-sphinx": smoke_gp_sphinx,
        "sphinx-gptheme": smoke_sphinx_gptheme,
        "sphinx-fonts": smoke_sphinx_fonts,
        "sphinx-argparse-neo": smoke_sphinx_argparse_neo,
    }
    if target not in runners:
        message = f"unknown smoke target: {target}"
        raise SystemExit(message)
    package = packages[target]
    runners[target](dist_dir, package.version)


def main() -> int:
    """Run the package tooling CLI."""
    parser = argparse.ArgumentParser(description="Workspace package tooling for CI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check-versions")
    subparsers.add_parser("print-packages")
    subparsers.add_parser("workspace-version")

    release_parser = subparsers.add_parser("release-metadata")
    release_parser.add_argument("tag")

    smoke_parser = subparsers.add_parser("smoke")
    smoke_parser.add_argument(
        "target",
        choices=[
            "root-install",
            "gp-sphinx",
            "sphinx-gptheme",
            "sphinx-fonts",
            "sphinx-argparse-neo",
        ],
    )
    smoke_parser.add_argument("--dist-dir", type=pathlib.Path)

    version_parser = subparsers.add_parser("print-version")
    version_parser.add_argument("package")

    args = parser.parse_args()

    if args.command == "check-versions":
        check_versions()
        return 0
    if args.command == "print-packages":
        for package_name in sorted(workspace_packages()):
            print(package_name)
        return 0
    if args.command == "workspace-version":
        print(workspace_version())
        return 0
    if args.command == "release-metadata":
        print(json.dumps(release_metadata(args.tag)))
        return 0
    if args.command == "smoke":
        smoke(args.target, dist_dir=args.dist_dir)
        return 0
    if args.command == "print-version":
        print(workspace_packages()[args.package].version)
        return 0

    message = "unreachable"
    raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
