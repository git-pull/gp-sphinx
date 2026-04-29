"""Tests for :mod:`gp_sphinx_astro_builder.content_config`."""

from __future__ import annotations

import typing as t

from gp_sphinx_astro_builder.content_config import render_content_config

if t.TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion


def test_render_content_config_returns_string() -> None:
    """``render_content_config`` returns a non-empty TypeScript source string."""
    source = render_content_config()
    assert isinstance(source, str)
    assert source.strip()


def test_render_content_config_imports_canonical_zod_schemas() -> None:
    """The generated source imports the parity-tested theme schemas."""
    source = render_content_config()
    assert "from '@gp-sphinx-astro/theme/schemas/doctree'" in source
    assert "from '@gp-sphinx-astro/theme/schemas/symbol'" in source
    assert "from '@gp-sphinx-astro/theme/schemas/xref'" in source


def test_render_content_config_defines_three_collections() -> None:
    """The generated source declares ``docs``, ``api``, and ``xrefs`` collections."""
    source = render_content_config()
    assert "docs: defineCollection" in source
    assert "api: defineCollection" in source
    assert "xrefs: defineCollection" in source


def test_render_content_config_uses_glob_for_docs_and_file_for_data() -> None:
    """The generated source wires ``glob()`` for docs and ``file()`` for symbols/xrefs."""
    source = render_content_config()
    # glob() for the per-document JSON
    assert "glob({ pattern: '**/*.json', base: './src/content/docs' })" in source
    # file() for the flat-array data collections
    assert "file('src/content/api/symbols.json')" in source
    assert "file('xref-index.json')" in source


def test_render_content_config_emits_export_const_collections() -> None:
    """The generated source ends with the canonical ``export const collections``."""
    source = render_content_config()
    assert "export const collections" in source


def test_render_content_config_matches_snapshot(
    snapshot: SnapshotAssertion,
) -> None:
    """The full generated source is byte-stable against a syrupy snapshot."""
    assert render_content_config() == snapshot
