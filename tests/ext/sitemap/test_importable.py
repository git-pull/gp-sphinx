"""Scaffolding-level smoke tests for sphinx-gp-sitemap."""

from __future__ import annotations

import typing as t

import sphinx_gp_sitemap


def test_import_exposes_setup() -> None:
    assert callable(sphinx_gp_sitemap.setup)


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

    meta = sphinx_gp_sitemap.setup(t.cast("t.Any", _FakeApp()))
    assert meta["version"]
    assert meta["parallel_read_safe"] is True
    # Safe at True: page enumeration runs at build-finished in the main
    # process via app.env.found_docs (env-merged across parallel-read
    # workers), so no per-handler state needs merging.
    assert meta["parallel_write_safe"] is True

    assert "site_url" in registered
    assert "sitemap_url_scheme" in registered
    assert "sitemap_filename" in registered
    # No builder-inited / html-page-context: the rewrite collects pages
    # at build-finished time so incremental builds emit a complete
    # sitemap (Sphinx fires html-page-context only for re-written pages).
    assert "builder-inited" not in connected
    assert "html-page-context" not in connected
    assert "config-inited" in connected
    assert "build-finished" in connected
