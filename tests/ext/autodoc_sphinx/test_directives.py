"""Tests for autodoc sphinx config directives."""

from __future__ import annotations

from sphinx_autodoc_sphinx import setup
from sphinx_autodoc_sphinx._directives import (
    discover_config_value,
    discover_config_values,
    render_config_index_markup,
    render_config_value_markup,
)


def test_extension_setup() -> None:
    """The extension setup function is importable."""
    assert callable(setup)


def test_config_index_discovers_registered_values() -> None:
    """The helper includes config values registered via setup()."""
    values = discover_config_values("sphinx_fonts")
    names = {item.name for item in values}
    assert "sphinx_fonts" in names
    assert "sphinx_font_preload" in names


def test_config_blocks_render_confval_entries() -> None:
    """Detailed rendering produces confval blocks for downstream docs."""
    value = next(
        item
        for item in discover_config_values("sphinx_argparse_neo")
        if item.name == "argparse_show_defaults"
    )
    markup = render_config_value_markup(value)
    assert ".. confval:: argparse_show_defaults" in markup
    assert ":default: ``True``" in markup


def test_discover_config_value_resolves_qualified_paths() -> None:
    """Single-value lookup accepts ``module_name.option`` paths."""
    value = discover_config_value("sphinx_fonts.sphinx_font_preload")
    assert value.name == "sphinx_font_preload"
    assert value.module_name == "sphinx_fonts"


def test_config_index_renders_summary_table() -> None:
    """The summary index renders a real list-table instead of placeholder text."""
    markup = render_config_index_markup("sphinx_fonts")
    assert ".. list-table::" in markup
    assert "sphinx_font_css_variables" in markup
