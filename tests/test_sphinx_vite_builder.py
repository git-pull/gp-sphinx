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
    assert __version__ == "0.0.1a17"


class _FakeApp:
    """Minimal Sphinx-app stand-in for setup() smoke tests.

    Carries the slice of ``sphinx.application.Sphinx`` that
    :func:`sphinx_vite_builder.setup` touches: ``add_config_value`` for
    the two extension config keys, and ``connect`` for the lifecycle
    handlers.
    """

    def __init__(self) -> None:
        self.config_values: list[tuple[str, dict[str, object]]] = []
        self.events: list[tuple[str, object]] = []

    def add_config_value(self, name: str, **kwargs: object) -> None:
        self.config_values.append((name, kwargs))

    def connect(self, event: str, callback: object) -> None:
        self.events.append((event, callback))


def test_setup_returns_safety_metadata() -> None:
    """``setup`` registers the extension and returns parallel-safety flags."""
    metadata = setup(_FakeApp())  # type: ignore[arg-type]
    assert metadata["parallel_read_safe"] is True
    assert metadata["parallel_write_safe"] is True
    assert metadata["version"] == __version__


def test_setup_registers_mode_config_value() -> None:
    """setup() registers sphinx_vite_builder_mode."""
    fake = _FakeApp()
    setup(fake)  # type: ignore[arg-type]
    names = [name for name, _ in fake.config_values]
    assert "sphinx_vite_builder_mode" in names


def test_setup_registers_root_config_value() -> None:
    """setup() registers sphinx_vite_builder_root."""
    fake = _FakeApp()
    setup(fake)  # type: ignore[arg-type]
    names = [name for name, _ in fake.config_values]
    assert "sphinx_vite_builder_root" in names


def test_setup_connects_lifecycle_events() -> None:
    """setup() connects to builder-inited and build-finished."""
    fake = _FakeApp()
    setup(fake)  # type: ignore[arg-type]
    event_names = [name for name, _ in fake.events]
    assert "builder-inited" in event_names
    assert "build-finished" in event_names


def test_extension_entry_point_is_discoverable() -> None:
    """The ``sphinx.extensions`` entry point lands on the right module."""
    eps = importlib.metadata.entry_points(group="sphinx.extensions")
    matched = [ep for ep in eps if ep.name == "sphinx-vite-builder"]
    assert matched, "sphinx-vite-builder entry point not discoverable"
    assert matched[0].value == "sphinx_vite_builder"


def test_top_level_exports() -> None:
    """The package's public surface is the documented two symbols."""
    assert sphinx_vite_builder.__all__ == ("__version__", "setup")
