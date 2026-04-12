"""Shared fixtures for pytest-fixture doctree and integration tests."""

from __future__ import annotations

import pathlib

import pytest


def _ensure_named_dir(root: pathlib.Path, name: str) -> pathlib.Path:
    """Return a stable child directory under ``root``."""
    path = root / name
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="session")
def spf_suite_root(
    tmp_path_factory: pytest.TempPathFactory,
) -> pathlib.Path:
    """Return a shared session root for synthetic fixture scenarios."""
    return tmp_path_factory.mktemp("spf-suite")


@pytest.fixture(scope="session")
def spf_doctree_root(
    spf_suite_root: pathlib.Path,
) -> pathlib.Path:
    """Return the shared doctree scenario root."""
    return _ensure_named_dir(spf_suite_root, "doctree")


@pytest.fixture(scope="session")
def spf_html_root(
    spf_suite_root: pathlib.Path,
) -> pathlib.Path:
    """Return the shared HTML integration scenario root."""
    return _ensure_named_dir(spf_suite_root, "html")
