"""Unit tests for _config_fact_rows and related tree output in autodoc-sphinx."""

from __future__ import annotations

import typing as t

from docutils import nodes
from sphinx_autodoc_layout._sections import ApiFactRow

from sphinx_autodoc_sphinx._directives import (
    SphinxConfigValue,
    _config_fact_rows,
    _is_complex_default,
    _make_default_block,
)


def _make_value(
    name: str = "demo_option",
    default: object = True,
    rebuild: str = "env",
    types: object = (bool,),
    module_name: str = "demo_ext",
    description: str = "",
) -> SphinxConfigValue:
    return SphinxConfigValue(
        module_name=module_name,
        name=name,
        default=default,
        rebuild=rebuild,
        types=types,
        description=description,
    )


def _rows_by_label(rows: t.Sequence[ApiFactRow]) -> dict[str, nodes.Node]:
    return {row.label: row.body for row in rows}


def test_config_fact_rows_produces_three_rows() -> None:
    """_config_fact_rows returns exactly Type, Default, Registered by."""
    value = _make_value()
    rows = _config_fact_rows(value)

    labels = [row.label for row in rows]
    assert labels == ["Type", "Default", "Registered by"]


def test_config_fact_rows_type_from_types_tuple() -> None:
    """Type row reflects the types tuple on the config value."""
    value = _make_value(types=(bool, str))
    rows = _config_fact_rows(value)

    by_label = _rows_by_label(rows)
    type_text = by_label["Type"].astext()
    assert "bool" in type_text
    assert "str" in type_text


def test_config_fact_rows_type_fallback_when_no_types() -> None:
    """When types is empty, Type falls back to the default value's type."""
    value = _make_value(default=42, types=())
    rows = _config_fact_rows(value)

    by_label = _rows_by_label(rows)
    assert "int" in by_label["Type"].astext()


def test_config_fact_rows_simple_default_uses_paragraph_literal() -> None:
    """Simple defaults (short repr) use a paragraph+literal, not a literal_block."""
    value = _make_value(default=True)
    rows = _config_fact_rows(value)

    by_label = _rows_by_label(rows)
    default_body = by_label["Default"]
    assert isinstance(default_body, nodes.paragraph)
    assert not any(isinstance(c, nodes.literal_block) for c in default_body.children)
    assert "True" in default_body.astext()


def test_config_fact_rows_complex_default_uses_literal_block() -> None:
    """Complex defaults (long repr) produce a literal_block with python highlighting."""
    complex_default = {f"key_{i}": f"value_{i}" for i in range(10)}
    assert _is_complex_default(complex_default), "fixture default should be complex"

    value = _make_value(default=complex_default, types=())
    rows = _config_fact_rows(value)

    by_label = _rows_by_label(rows)
    default_body = by_label["Default"]
    assert isinstance(default_body, nodes.literal_block)
    assert default_body.get("language") == "python"


def test_config_fact_rows_registered_by_contains_module_and_setup() -> None:
    """Registered by row names the module with .setup() suffix."""
    value = _make_value(module_name="my_extension")
    rows = _config_fact_rows(value)

    by_label = _rows_by_label(rows)
    registered = by_label["Registered by"].astext()
    assert "my_extension" in registered
    assert "setup()" in registered


def test_config_fact_rows_string_default_with_warning_value() -> None:
    """String defaults stay as paragraph+literal (repr is short enough)."""
    value = _make_value(default="warning", types=(str,))
    rows = _config_fact_rows(value)

    by_label = _rows_by_label(rows)
    default_body = by_label["Default"]
    assert isinstance(default_body, nodes.paragraph)
    assert "warning" in default_body.astext()


def test_config_fact_rows_none_default_type_is_none() -> None:
    """None default with empty types produces a None type label."""
    value = _make_value(default=None, types=())
    rows = _config_fact_rows(value)

    by_label = _rows_by_label(rows)
    assert "None" in by_label["Type"].astext()


def test_config_fact_rows_produces_api_fact_row_instances() -> None:
    """All returned objects are ApiFactRow dataclass instances."""
    value = _make_value()
    rows = _config_fact_rows(value)

    for row in rows:
        assert isinstance(row, ApiFactRow)
        assert isinstance(row.label, str)
        assert isinstance(row.body, nodes.Node)


def test_make_default_block_produces_python_literal_block() -> None:
    """_make_default_block always sets language=python and force=False."""
    block = _make_default_block({"key": "value"})

    assert isinstance(block, nodes.literal_block)
    assert block.get("language") == "python"
    assert block.get("force") is False
    assert block.get("linenos") is False
    assert "key" in block.astext()


def test_is_complex_default_threshold() -> None:
    """Short reprs are not complex; long reprs are."""
    assert not _is_complex_default(True)
    assert not _is_complex_default("warning")
    assert not _is_complex_default(42)
    assert _is_complex_default(frozenset(range(20)))
    assert _is_complex_default({f"k{i}": f"v{i}" for i in range(10)})
