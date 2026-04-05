"""Tests for autodoc sphinx config directives."""

from __future__ import annotations

import typing as t

import pytest

from sphinx_autodoc_sphinx import setup
from sphinx_autodoc_sphinx._directives import (
    SphinxConfigValue,
    _is_complex_default,
    _make_default_block,
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


class IsComplexCase(t.NamedTuple):
    """Test case for _is_complex_default."""

    value: object
    expected: bool
    test_id: str


@pytest.mark.parametrize(
    "case",
    [
        IsComplexCase(True, False, "bool_simple"),
        IsComplexCase("warning", False, "short_string"),
        IsComplexCase({}, False, "empty_dict"),
        IsComplexCase({"k" * 5: "v" * 60}, True, "long_dict"),
        IsComplexCase(frozenset(range(15)), True, "large_frozenset"),
    ],
    ids=lambda c: c.test_id,
)
def test_is_complex_default(case: IsComplexCase) -> None:
    """Values with repr > 60 chars are flagged as complex."""
    assert _is_complex_default(case.value) == case.expected


def test_make_default_block_produces_literal_block() -> None:
    """_make_default_block returns a literal_block with language='python'."""
    block = _make_default_block({"key": "value"})
    assert block["language"] == "python"
    assert "key" in block.astext()


def test_render_config_value_markup_omits_default_for_complex() -> None:
    """Complex defaults omit the :default: field; simple defaults keep it."""
    complex_value = SphinxConfigValue(
        "demo_ext",
        "demo_map",
        {"key": "https://example.com/very/long/url/path/that/exceeds/threshold"},
        "env",
        (dict,),
    )
    assert ":default:" not in render_config_value_markup(complex_value)

    simple_value = SphinxConfigValue("demo_ext", "demo_flag", True, "html", (bool,))
    assert ":default: ``True``" in render_config_value_markup(simple_value)
