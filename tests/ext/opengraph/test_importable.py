"""Scaffolding-level smoke tests for gp-opengraph."""

from __future__ import annotations

import types
import typing as t

import gp_opengraph


def test_import_exposes_setup() -> None:
    assert callable(gp_opengraph.setup)


def test_setup_registers_config_values_and_connects_hook() -> None:
    """setup() registers every ogp_* config value and the html-page-context hook."""
    registered: list[str] = []
    connected: list[str] = []

    class _FakeApp:
        def add_config_value(self, name: str, *args: t.Any, **kwargs: t.Any) -> None:
            registered.append(name)

        def connect(self, event: str, handler: t.Callable[..., t.Any]) -> None:
            connected.append(event)

    meta = gp_opengraph.setup(t.cast("t.Any", _FakeApp()))
    assert meta["version"]
    assert meta["parallel_read_safe"] is True
    assert meta["parallel_write_safe"] is True

    assert "ogp_site_url" in registered
    assert "ogp_image" in registered
    assert "ogp_custom_meta_tags" in registered
    assert "html-page-context" in connected
    assert "config-inited" in connected

    # Keeps downstream static-analyzers happy — types unused otherwise.
    _ = types.ModuleType
