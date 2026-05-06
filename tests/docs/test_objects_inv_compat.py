r"""Risk-1 mitigation: prove the per-package migration loses no xref targets.

The pre-migration ``objects.inv`` is captured in
``tests/docs/__snapshots__/objects-inv-baseline.txt`` (one
``<domain>\t<name>`` line per entry, sorted). Every subsequent
docs build must produce a SUPERSET — no entry from the baseline
may disappear, even if entries move between docnames.

The fixture builds the live ``docs/`` tree once per test session
via ``sphinx.application.Sphinx`` against a tmp output dir, then
parses the generated ``objects.inv``. Cost: ~10-30 seconds per
session, paid once.

Group G4 of the migration plan refreshes this snapshot to the
post-migration superset once every package has migrated.
"""

from __future__ import annotations

import io
import pathlib

import pytest
from sphinx.util.inventory import InventoryFile

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SNAPSHOT = REPO_ROOT / "tests" / "docs" / "__snapshots__" / "objects-inv-baseline.txt"


def _join(base: str, target: str) -> str:
    """Inventory join function — return ``target`` since paths are relative."""
    return target


def _flatten_inventory(inv_path: pathlib.Path) -> set[str]:
    """Return ``{domain<TAB>name, ...}`` for every entry in ``inv_path``."""
    with inv_path.open("rb") as handle:
        inventory = InventoryFile.load(handle, "", _join)
    return {
        f"{domain}\t{name}" for domain, entries in inventory.items() for name in entries
    }


# Risk 1 (woven plan §5.3) is specifically about py-domain
# cross-references not being lost during the migration. std:doc /
# std:label entries are EXPECTED to change as docnames reorganize
# (e.g. packages/sphinx-fonts -> packages/sphinx-fonts/index +
# /how-to + /reference) and rediraffe handles those URL-level
# redirects for legacy consumers. We assert the *xref-stable*
# domains form a superset.
_XREF_STABLE_DOMAIN_PREFIXES: tuple[str, ...] = (
    "py:",
    "rst:",
    "argparse:",
)


def _baseline_keys() -> set[str]:
    """Load the committed baseline filtered to xref-stable domains."""
    text = SNAPSHOT.read_text(encoding="utf-8")
    keys: set[str] = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        domain = line.split("\t", 1)[0]
        if any(domain.startswith(prefix) for prefix in _XREF_STABLE_DOMAIN_PREFIXES):
            keys.add(line)
    return keys


@pytest.fixture(scope="module")
def _live_objects_inv(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """Build the live ``docs/`` tree once and return the resulting inventory path.

    Uses ``sphinx.application.Sphinx`` directly so the build is
    hermetic against the developer's working ``docs/_build/`` cache.
    Module-scoped — built once per pytest module run.
    """
    from sphinx.application import Sphinx

    src_dir = REPO_ROOT / "docs"
    out_dir = tmp_path_factory.mktemp("objects-inv")
    doctree_dir = out_dir / ".doctrees"
    html_dir = out_dir / "html"

    # status/warning streams swallowed; CI's `just build-docs` is the
    # build whose warnings are surfaced under -W.
    status = io.StringIO()
    warning = io.StringIO()
    app = Sphinx(
        srcdir=str(src_dir),
        confdir=str(src_dir),
        outdir=str(html_dir),
        doctreedir=str(doctree_dir),
        buildername="dirhtml",
        status=status,
        warning=warning,
        freshenv=True,
    )
    app.build()
    inv_path = html_dir / "objects.inv"
    if not inv_path.is_file():
        pytest.fail(f"sphinx build produced no objects.inv at {inv_path}")
    return inv_path


@pytest.mark.integration
def test_objects_inv_is_superset_of_baseline(
    _live_objects_inv: pathlib.Path,
) -> None:
    """No baseline cross-reference target is missing from the live build."""
    live_keys = _flatten_inventory(_live_objects_inv)
    baseline = _baseline_keys()
    missing = baseline - live_keys
    assert not missing, (
        f"{len(missing)} cross-reference target(s) lost since baseline:\n"
        + "\n".join(sorted(missing)[:20])
        + ("\n..." if len(missing) > 20 else "")
    )


def test_baseline_snapshot_is_sorted_and_unique() -> None:
    """The baseline file is canonical: sorted, no duplicates, no blanks."""
    text = SNAPSHOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    non_empty = [line for line in lines if line.strip()]
    assert non_empty == sorted(non_empty), "baseline must be sorted"
    assert len(non_empty) == len(set(non_empty)), "baseline must be unique"


def test_baseline_snapshot_has_expected_shape() -> None:
    r"""Every line is ``<domain>\t<name>`` (single tab, non-empty halves)."""
    text = SNAPSHOT.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        assert line.count("\t") == 1, f"line {lineno}: expected one tab, got {line!r}"
        domain, name = line.split("\t", 1)
        assert domain, f"line {lineno}: empty domain"
        assert name, f"line {lineno}: empty name"
