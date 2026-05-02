"""Smoke tests for gp_sphinx_vite package skeleton.

Subprocess orchestration tests (spawn / teardown / idempotence /
SIGINT / SIGHUP) land alongside the implementation in subsequent
commits. This file proves the package skeleton is wired up.
"""

from __future__ import annotations

import importlib.metadata

from gp_sphinx_vite import __version__, setup


def test_version_matches_workspace_lock() -> None:
    """Version follows gp-sphinx workspace lockstep."""
    assert __version__ == "0.0.1a12"


def test_setup_registers_mode_config_value() -> None:
    """setup() registers gp_sphinx_vite_mode."""
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeApp:
        def add_config_value(self, name: str, **kwargs: object) -> None:
            calls.append((name, kwargs))

    fake = FakeApp()
    setup(fake)  # type: ignore[arg-type]
    names = [name for name, _ in calls]
    assert "gp_sphinx_vite_mode" in names


def test_setup_registers_root_config_value() -> None:
    """setup() registers gp_sphinx_vite_root."""
    calls: list[str] = []

    class FakeApp:
        def add_config_value(self, name: str, **_: object) -> None:
            calls.append(name)

    fake = FakeApp()
    setup(fake)  # type: ignore[arg-type]
    assert "gp_sphinx_vite_root" in calls


def test_setup_returns_parallel_safe_metadata() -> None:
    """Both parallel-safe flags are True (no shared mutable state)."""

    class FakeApp:
        def add_config_value(self, name: str, **_: object) -> None:
            pass

    metadata = setup(FakeApp())  # type: ignore[arg-type]
    assert metadata["parallel_read_safe"] is True
    assert metadata["parallel_write_safe"] is True
    assert metadata["version"] == __version__


def test_entry_point_is_discoverable() -> None:
    """The sphinx.extensions entry point is registered for gp-sphinx-vite."""
    eps = importlib.metadata.entry_points(group="sphinx.extensions")
    matched = [ep for ep in eps if ep.name == "gp-sphinx-vite"]
    assert matched, "gp-sphinx-vite entry point not discoverable"
    assert matched[0].value == "gp_sphinx_vite"
