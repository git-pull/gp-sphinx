"""Tests for sphinx_autodoc_sphinx helpers."""

from __future__ import annotations

from sphinx_autodoc_sphinx import setup
from sphinx_autodoc_sphinx._directives import (
    discover_config_values,
    render_config_value_markup,
)


def test_sphinx_autodoc_sphinx_setup_is_importable() -> None:
    """The extension setup function is importable."""
    assert callable(setup)


def test_config_values_discovers_registered_options() -> None:
    """The helper captures config values from an extension setup hook."""
    values = discover_config_values("sphinx_fonts")
    names = {value.name for value in values}
    assert names == {
        "sphinx_fonts",
        "sphinx_font_fallbacks",
        "sphinx_font_css_variables",
        "sphinx_font_preload",
    }


def test_config_markup_contains_default_and_rebuild() -> None:
    """Rendered config markup shows the default and rebuild target."""
    value = next(
        item
        for item in discover_config_values("sphinx_argparse_neo")
        if item.name == "argparse_show_defaults"
    )
    markup = render_config_value_markup(value)
    assert ":default: ``True``" in markup
    assert "Rebuild: ``html``" in markup
