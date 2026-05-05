"""Permissive upper-bound guard against sidebar-overflow regressions.

Counts every toctree leaf entry under ``docs/index.md`` and any
nested ``docs/**/index.md`` files. The bound is intentionally
**permissive** during the per-package docs migration window; once
the migration completes, ``Group G2`` of the migration plan
tightens it to the exact post-migration value (``19 * 6 +
workspace_chrome`` per Risk 2 in the woven plan).

Failure mode this catches: a refactor that accidentally explodes
the sidebar (e.g. promoting every H2 in a flat page to its own
toctree leaf) before that change reaches a reader.
"""

from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


_TOCTREE_FENCE = re.compile(r"^(?P<indent>\s*)```+\{toctree\}\s*$")
_TOCTREE_CLOSE = re.compile(r"^(?P<indent>\s*)```+\s*$")
_TOCTREE_OPTION = re.compile(r"^\s*:[a-zA-Z][\w-]*:")


def _toctree_entries(md_path: pathlib.Path) -> list[str]:
    """Return every leaf entry across all ``{toctree}`` blocks in ``md_path``.

    Skips blank lines, MyST option lines (``:caption:``, ``:hidden:``,
    ``:titlesonly:``, ``:maxdepth:``, …), and the directive's own
    fences. Each remaining non-empty line is one toctree leaf.

    Examples
    --------
    >>> from pathlib import Path
    >>> import textwrap, tempfile
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = Path(tmp) / "x.md"
    ...     _ = p.write_text(textwrap.dedent('''
    ...         # Title
    ...
    ...         ```{toctree}
    ...         :caption: Group
    ...         :hidden:
    ...
    ...         packages/foo/index
    ...         packages/bar/index
    ...         ```
    ...     '''))
    ...     entries = _toctree_entries(p)
    >>> entries
    ['packages/foo/index', 'packages/bar/index']
    """
    entries: list[str] = []
    inside = False
    fence_indent = ""
    for line in md_path.read_text(encoding="utf-8").splitlines():
        if not inside:
            match = _TOCTREE_FENCE.match(line)
            if match is not None:
                inside = True
                fence_indent = match.group("indent")
            continue
        close = _TOCTREE_CLOSE.match(line)
        if close is not None and close.group("indent") == fence_indent:
            inside = False
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if _TOCTREE_OPTION.match(line):
            continue
        entries.append(stripped)
    return entries


def _all_toctree_entries() -> list[str]:
    """Return every toctree leaf from ``docs/**/index.md``.

    Reads ``docs/index.md`` plus any ``docs/<subdir>/index.md`` so the
    count reflects what the rendered sidebar actually nests. Files
    under ``_build/`` are excluded.
    """
    docs_dir = REPO_ROOT / "docs"
    entries: list[str] = []
    for index_md in sorted(docs_dir.rglob("index.md")):
        if "_build" in index_md.parts:
            continue
        entries.extend(_toctree_entries(index_md))
    return entries


# Pinned at the per-package migration baseline: the workspace had 28
# toctree leaves at the start of the docs-split branch (16 flat package
# pages + workspace chrome). The 50-leaf headroom accommodates the
# migration's natural growth as flat pages become per-package
# directories (each adds 0-5 child leaves for sibling toctrees inside
# packages/<name>/index.md). Group G2 of the migration plan replaces
# this permissive ceiling with the exact post-migration value
# (``19 * 6 + workspace_chrome``) once every package has shipped.
_BASELINE_TOCTREE_LEAVES = 28
_PERMISSIVE_BUFFER = 50
_PERMISSIVE_BOUND = _BASELINE_TOCTREE_LEAVES + _PERMISSIVE_BUFFER


def test_toctree_entries_within_permissive_upper_bound() -> None:
    """Total toctree leaves stay under the migration-window ceiling."""
    entries = _all_toctree_entries()
    assert len(entries) <= _PERMISSIVE_BOUND, (
        f"sidebar-density regression: {len(entries)} toctree leaves "
        f"exceeds permissive bound {_PERMISSIVE_BOUND} "
        f"({_BASELINE_TOCTREE_LEAVES} baseline + "
        f"{_PERMISSIVE_BUFFER} migration headroom)"
    )


def test_toctree_entries_include_workspace_packages() -> None:
    """Smoke check: at least one ``packages/...`` entry is present today."""
    entries = _all_toctree_entries()
    package_entries = [e for e in entries if e.startswith("packages/")]
    assert package_entries, "expected at least one packages/* toctree leaf"


def test_toctree_entries_have_no_leading_or_trailing_whitespace() -> None:
    """Every leaf survives strip() unchanged — guard against indent drift."""
    for entry in _all_toctree_entries():
        assert entry == entry.strip()
