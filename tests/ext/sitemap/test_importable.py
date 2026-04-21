"""Scaffolding-level smoke tests for gp-sitemap."""

from __future__ import annotations

import typing as t

import gp_sitemap


def test_import_exposes_setup() -> None:
    assert callable(gp_sitemap.setup)


def test_setup_registers_config_values_and_connects_hooks() -> None:
    """setup() registers every sitemap_* config value and three event hooks."""
    registered: list[str] = []
    connected: list[str] = []

    class _FakeConfig:
        sitemap_show_lastmod = False

    class _FakeApp:
        config = _FakeConfig()

        def add_config_value(self, name: str, *args: t.Any, **kwargs: t.Any) -> None:
            registered.append(name)

        def connect(self, event: str, handler: t.Callable[..., t.Any]) -> None:
            connected.append(event)

        def setup_extension(self, name: str) -> None:
            pass

    meta = gp_sitemap.setup(t.cast("t.Any", _FakeApp()))
    assert meta["version"]
    assert meta["parallel_read_safe"] is True
    assert meta["parallel_write_safe"] is True

    assert "site_url" in registered
    assert "sitemap_url_scheme" in registered
    assert "sitemap_filename" in registered
    assert "builder-inited" in connected
    assert "html-page-context" in connected
    assert "build-finished" in connected
