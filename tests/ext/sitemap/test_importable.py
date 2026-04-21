"""Scaffolding-level smoke tests for gp-sitemap."""

from __future__ import annotations

import gp_sitemap


def test_import_exposes_setup() -> None:
    assert callable(gp_sitemap.setup)


def test_setup_returns_extension_metadata() -> None:
    meta = gp_sitemap.setup(app=None)  # type: ignore[arg-type]
    assert meta["version"]
    assert meta["parallel_read_safe"] is True
    assert meta["parallel_write_safe"] is True
