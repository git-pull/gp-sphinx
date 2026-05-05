"""Stale-legacy-page CI gate (G1 of the per-package docs migration).

Asserts no flat ``docs/packages/<name>.md`` co-exists with a
per-package ``docs/packages/<name>/index.md``. During the migration
window (Group E) such co-existence would silently shadow either form
depending on Sphinx's docname resolution; tripping this gate makes
that drift loud.

Once Group E completes, every flat per-package page should be gone
(replaced by the per-package directory). The check therefore also
fails if any flat per-package ``<name>.md`` lingers when the
``<name>/`` directory exists.
"""

from __future__ import annotations

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGES_DIR = REPO_ROOT / "docs" / "packages"

# packages/index.md is the workspace inventory page, not a per-package
# legacy page; exclude it from the check.
_INDEX_NAME = "index"


def test_no_per_package_dir_co_exists_with_flat_md() -> None:
    """No ``<name>.md`` shares a stem with an existing ``<name>/`` directory."""
    flat_stems = {
        path.stem for path in PACKAGES_DIR.glob("*.md") if path.stem != _INDEX_NAME
    }
    dir_stems = {
        path.name
        for path in PACKAGES_DIR.iterdir()
        if path.is_dir() and (path / "index.md").is_file()
    }
    overlap = flat_stems & dir_stems
    assert not overlap, (
        "Stale legacy flat pages co-exist with per-package directories: "
        f"{sorted(overlap)} — delete the flat <name>.md files."
    )
