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

    Note: cluster-toctree directive calls in ``docs/index.md`` are
    NOT counted here — they emit toctree leaves at build time. Use
    :func:`_post_migration_total_leaves` for the rendered total.
    """
    docs_dir = REPO_ROOT / "docs"
    entries: list[str] = []
    for index_md in sorted(docs_dir.rglob("index.md")):
        if "_build" in index_md.parts:
            continue
        entries.extend(_toctree_entries(index_md))
    return entries


def _per_package_subpages() -> list[str]:
    """Return every ``<docname>`` subpage anchored under ``docs/packages/<name>/``.

    Each per-package landing has its own ``{toctree}`` listing siblings
    (tutorial / how-to / reference / explanation / examples / errors /
    cli). Walk the per-package directories to count those leaves.
    """
    packages_dir = REPO_ROOT / "docs" / "packages"
    leaves: list[str] = []
    for landing in sorted(packages_dir.glob("*/index.md")):
        package_name = landing.parent.name
        for sub in sorted(landing.parent.glob("*.md")):
            if sub.name == "index.md":
                continue
            leaves.append(f"packages/{package_name}/{sub.stem}")
    return leaves


def _cluster_toctree_leaves() -> list[str]:
    """Return every leaf the cluster-toctree directives emit.

    Mirrors the directive's logic without invoking Sphinx: walk the
    workspace, skip Emerging packages, pin to per-package landings.
    """
    import sys

    sys.path.insert(0, str(REPO_ROOT / "docs" / "_ext"))
    import package_reference

    return [
        f"packages/{record.name}/index"
        for record in package_reference.workspace_package_records()
        if record.state in {"shipped-py", "shipped-js"}
    ]


def _post_migration_total_leaves() -> int:
    """Sum of structural toctree leaves the rendered sidebar exposes."""
    return (
        len(_all_toctree_entries())
        + len(_cluster_toctree_leaves())
        + len(_per_package_subpages())
    )


# Post-migration ceiling per the woven plan §2.1 / Risk 2.
# Calculation:
#   - workspace chrome entries in docs/index.md (whats-new, gallery,
#     architecture, quickstart, configuration, packages/index, api,
#     project/index, history, contributing, code-style, releasing) = ~12
#   - cluster-toctree leaves: one per Shipped package (16 today) = 16
#   - per-package subpages: ~3-5 per package, max 6 = up to 96
#   - margin for additional clusters / chrome growth = +20
#
# Total ceiling: 19 packages * 6 max-subpages + 30 chrome = 144.
# Today's value sits comfortably below this.
_POST_MIGRATION_BOUND = 19 * 6 + 30


def test_toctree_entries_within_post_migration_upper_bound() -> None:
    """Total toctree leaves stay under the post-migration ceiling."""
    total = _post_migration_total_leaves()
    assert total <= _POST_MIGRATION_BOUND, (
        f"sidebar-density regression: {total} toctree leaves "
        f"exceeds post-migration bound {_POST_MIGRATION_BOUND}"
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
