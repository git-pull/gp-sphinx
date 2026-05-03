"""Tests for the ``sphinx-vite-builder`` package wiring.

Covers package metadata + entry-point discovery; subprocess and
backend behaviour live in dedicated test modules so each suite stays
focused.
"""

from __future__ import annotations

import importlib.metadata

import sphinx_vite_builder
from sphinx_vite_builder import __version__, setup


def test_version_matches_workspace_lock() -> None:
    """Version follows the gp-sphinx workspace lockstep."""
    assert __version__ == "0.0.1a16.dev0"


def test_setup_returns_safety_metadata() -> None:
    """``setup`` registers the extension and returns parallel-safety flags."""

    class _FakeApp:
        pass

    metadata = setup(_FakeApp())  # type: ignore[arg-type]
    assert metadata["parallel_read_safe"] is True
    assert metadata["parallel_write_safe"] is True
    assert metadata["version"] == __version__


def test_extension_entry_point_is_discoverable() -> None:
    """The ``sphinx.extensions`` entry point lands on the right module."""
    eps = importlib.metadata.entry_points(group="sphinx.extensions")
    matched = [ep for ep in eps if ep.name == "sphinx-vite-builder"]
    assert matched, "sphinx-vite-builder entry point not discoverable"
    assert matched[0].value == "sphinx_vite_builder"


def test_top_level_exports() -> None:
    """The package's public surface is the documented two symbols."""
    assert sphinx_vite_builder.__all__ == ("__version__", "setup")
