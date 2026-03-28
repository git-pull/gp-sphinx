"""Conftest.py (root-level) for gp-sphinx tests.

We keep this in root so pytest fixtures and doctest namespace fixtures are
available globally, and to avoid conftest.py from being included in the wheel.
"""

from __future__ import annotations

import pathlib

import pytest


@pytest.fixture(autouse=True)
def _doctest_namespace(
    doctest_namespace: dict[str, object],
    tmp_path: pathlib.Path,
) -> None:
    """Inject common fixtures into doctest namespace."""
    doctest_namespace["tmp_path"] = tmp_path
