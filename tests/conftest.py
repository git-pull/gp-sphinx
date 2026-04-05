"""Conftest.py (root-level) for gp-sphinx tests.

We keep this in root so pytest fixtures and doctest namespace fixtures are
available globally, and to avoid conftest.py from being included in the wheel.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

for src_path in sorted(
    (pathlib.Path(__file__).resolve().parents[1] / "packages").glob("*/src")
):
    src_str = str(src_path)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


@pytest.fixture(autouse=True)
def _doctest_namespace(
    doctest_namespace: dict[str, object],
    tmp_path: pathlib.Path,
) -> None:
    """Inject common fixtures into doctest namespace."""
    doctest_namespace["tmp_path"] = tmp_path
