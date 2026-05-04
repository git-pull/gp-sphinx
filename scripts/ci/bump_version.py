"""Rewrite the workspace version literal across pyproject, source, tests, and scripts.

The workspace keeps its version duplicated in several places:

- ``pyproject.toml`` (root + every publishable package)
- ``__version__`` / ``_EXTENSION_VERSION`` constants in package ``__init__.py``
- Sphinx ``setup()`` return-dict ``"version"`` keys
- ``tests/test_package_tools.py`` assertions
- ``smoke_gp_sphinx`` template in ``scripts/ci/package_tools.py``
- npm ``package.json`` ``version`` fields under ``astro/`` (SemVer prerelease form)
- TypeScript / Astro source literals under ``astro/`` (PEP 440 form)

Both PEP 440 (``0.0.1a16``) and the equivalent npm SemVer prerelease form
(``0.0.1-alpha.16``) are recognised by :func:`_alt_form`, so a single bump
call keeps Python and JS literals in lockstep.

``scripts/ci/package_tools.py check-versions`` catches drift between the
pyproject version and whatever the runtime source says, so any literal missed
by this bump will surface immediately after ``uv lock``.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import typing as t

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

try:
    from packaging.version import InvalidVersion, Version
except ImportError:  # pragma: no cover - packaging is a runtime dep via uv
    InvalidVersion = ValueError  # type: ignore[assignment,misc]
    Version = None  # type: ignore[assignment,misc]


#: Glob patterns (relative to the workspace root) that may contain version
#: literals. Order is informational only; rewrites are idempotent.
BUMP_GLOBS: t.Final[tuple[str, ...]] = (
    "pyproject.toml",
    "packages/*/pyproject.toml",
    "packages/*/src/**/*.py",
    "tests/**/*.py",
    "scripts/**/*.py",
    # Main-side JS-only / hybrid packages — gp-furo-tokens (pure JS) and
    # gp-furo-theme/web (vite asset pipeline nested inside a Python
    # package). Without these globs, JS package.json + TypeScript
    # version literals lag behind every Python bump.
    "packages/*/package.json",
    "packages/*/web/package.json",
    "packages/*/src/**/*.ts",
    # Astro JS stack — both PEP 440 and npm SemVer prerelease literals.
    # _alt_form() handles the form equivalence so one bump call covers both.
    "astro/package.json",
    "astro/packages/*/package.json",
    "astro/apps/*/package.json",
    "astro/packages/*/src/**/*.ts",
    "astro/apps/*/src/**/*.ts",
    "astro/apps/*/src/components/*.astro",
)

#: Path fragments to skip even if a glob matches them.
EXCLUDE_FRAGMENTS: t.Final[tuple[str, ...]] = (
    ".venv/",
    "/build/",
    "/dist/",
    "/.git/",
    "/node_modules/",
    "__pycache__/",
)

#: PEP 440 prerelease pattern: base ``X.Y.Z`` + kind ``a|b|rc`` + numeric tail.
_PEP_PRERELEASE_RE: t.Final[re.Pattern[str]] = re.compile(
    r"^(\d+(?:\.\d+)*)(a|b|rc)(\d+)$",
)

#: PEP 440 prerelease kind → npm SemVer prerelease label.
_NPM_KIND_BY_PEP: t.Final[dict[str, str]] = {
    "a": "alpha",
    "b": "beta",
    "rc": "rc",
}


def _alt_form(version: str) -> str | None:
    """Return the npm SemVer prerelease form of a PEP 440 version, or ``None``.

    Parameters
    ----------
    version : str
        PEP 440 version string. Stable releases (``1.2.3``) and any string
        that doesn't match :data:`_PEP_PRERELEASE_RE` return ``None``.

    Returns
    -------
    str | None
        The npm form (``0.0.1-alpha.16``) when ``version`` is a PEP 440
        prerelease (``a``/``b``/``rc``); otherwise ``None``.

    Examples
    --------
    >>> _alt_form("0.0.1a16")
    '0.0.1-alpha.16'
    >>> _alt_form("1.2.3b1")
    '1.2.3-beta.1'
    >>> _alt_form("1.2.3rc4")
    '1.2.3-rc.4'
    >>> _alt_form("1.2.3") is None
    True
    >>> _alt_form("not-a-version") is None
    True
    """
    match = _PEP_PRERELEASE_RE.match(version)
    if match is None:
        return None
    base, kind, num = match.groups()
    return f"{base}-{_NPM_KIND_BY_PEP[kind]}.{num}"


#: File-level opt-out sentinel. A line whose stripped content equals this
#: marker freezes the file's version literals — use in scenario fixtures
#: where the literal describes a bump relationship, not workspace state.
SKIP_FILE_MARKER: t.Final[str] = "# bump-version: skip-file"


def _workspace_root() -> pathlib.Path:
    """Return the repository root."""
    return pathlib.Path(__file__).resolve().parents[2]


def _read_root_version(root: pathlib.Path) -> str:
    """Return the root ``pyproject.toml`` version string.

    Parameters
    ----------
    root : pathlib.Path
        Repository root containing the root ``pyproject.toml``.

    Returns
    -------
    str
        Version string for the workspace root package.
    """
    with (root / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    return t.cast("str", data["project"]["version"])


def _validate_new_version(new_version: str, old_version: str) -> None:
    """Validate that ``new_version`` is PEP 440 and not the same as ``old_version``.

    Parameters
    ----------
    new_version : str
        Proposed new version.
    old_version : str
        Current workspace version.
    """
    if new_version == old_version:
        message = f"new version {new_version!r} equals current version"
        raise SystemExit(message)
    if Version is not None:
        try:
            Version(new_version)
        except InvalidVersion as exc:
            message = f"invalid PEP 440 version {new_version!r}: {exc}"
            raise SystemExit(message) from exc


def _iter_candidate_files(root: pathlib.Path) -> t.Iterator[pathlib.Path]:
    """Yield files matching any :data:`BUMP_GLOBS` pattern, deduplicated."""
    seen: set[pathlib.Path] = set()
    for pattern in BUMP_GLOBS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            as_posix = resolved.as_posix()
            if any(fragment in as_posix for fragment in EXCLUDE_FRAGMENTS):
                continue
            seen.add(resolved)
            yield path


def _rewrite_file(
    path: pathlib.Path,
    old_version: str,
    new_version: str,
) -> int:
    """Rewrite ``old_version`` -> ``new_version`` in ``path``; return replacement count.

    Both the primary PEP 440 form and the equivalent npm SemVer prerelease
    form (when applicable) are rewritten in a single pass so that a Python
    bump (e.g. ``0.0.1a16 → 0.0.1a17``) also updates JS ``package.json``
    literals (``0.0.1-alpha.16 → 0.0.1-alpha.17``).

    Parameters
    ----------
    path : pathlib.Path
        File to rewrite.
    old_version : str
        Literal to replace. Matched verbatim; no regex.
    new_version : str
        Replacement literal.

    Returns
    -------
    int
        Number of occurrences replaced across both forms. Zero if the file
        did not change.
    """
    original = path.read_text()
    if any(line.strip() == SKIP_FILE_MARKER for line in original.splitlines()):
        return 0

    pairs: list[tuple[str, str]] = [(old_version, new_version)]
    old_alt = _alt_form(old_version)
    new_alt = _alt_form(new_version)
    if old_alt is not None and new_alt is not None:
        pairs.append((old_alt, new_alt))

    updated = original
    replacements = 0
    for old, new in pairs:
        if old in updated:
            replacements += updated.count(old)
            updated = updated.replace(old, new)

    if replacements == 0:
        return 0
    path.write_text(updated)
    return replacements


def bump_workspace_version(
    new_version: str,
    *,
    root: pathlib.Path | None = None,
) -> list[tuple[pathlib.Path, int]]:
    """Rewrite every workspace version literal to ``new_version``.

    Parameters
    ----------
    new_version : str
        Target version, validated as PEP 440.
    root : pathlib.Path | None
        Repository root. Defaults to the script's enclosing workspace.

    Returns
    -------
    list[tuple[pathlib.Path, int]]
        (path, replacement_count) pairs for every file touched.
    """
    workspace_root = root if root is not None else _workspace_root()
    old_version = _read_root_version(workspace_root)
    _validate_new_version(new_version, old_version)

    changes: list[tuple[pathlib.Path, int]] = []
    for path in _iter_candidate_files(workspace_root):
        count = _rewrite_file(path, old_version, new_version)
        if count:
            changes.append((path, count))
    return changes


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Rewrite the shared workspace version across every "
            "pyproject.toml, __init__.py, and test file."
        ),
    )
    parser.add_argument("new_version", help="Target version (PEP 440)")
    return parser


def main(argv: t.Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = _build_parser().parse_args(argv)
    root = _workspace_root()
    old_version = _read_root_version(root)
    changes = bump_workspace_version(args.new_version, root=root)

    total_replacements = sum(count for _, count in changes)
    print(f"  {old_version} -> {args.new_version}")
    for path, count in changes:
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        print(f"    {rel} ({count})")
    print(
        f"  {len(changes)} file(s) changed, {total_replacements} replacement(s)",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
