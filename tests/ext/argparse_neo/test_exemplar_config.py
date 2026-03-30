"""Tests for sphinx_argparse_neo.exemplar.ExemplarConfig."""

from __future__ import annotations

import types

from sphinx_argparse_neo.exemplar import ExemplarConfig


def test_from_sphinx_config_defaults() -> None:
    """Test ExemplarConfig.from_sphinx_config with empty namespace uses defaults."""
    cfg = ExemplarConfig.from_sphinx_config(types.SimpleNamespace())  # type: ignore[arg-type]

    assert cfg.examples_term_suffix == "examples"
    assert cfg.command_prefix == "$ "
    assert cfg.code_language == "console"
    assert cfg.reorder_usage_before_examples is True


def test_from_sphinx_config_overrides() -> None:
    """Test ExemplarConfig.from_sphinx_config respects Sphinx config attributes."""
    mock_config = types.SimpleNamespace(
        argparse_examples_term_suffix="Examples",
        argparse_examples_command_prefix="% ",
        argparse_examples_code_language="bash",
    )
    cfg = ExemplarConfig.from_sphinx_config(mock_config)  # type: ignore[arg-type]

    assert cfg.examples_term_suffix == "Examples"
    assert cfg.command_prefix == "% "
    assert cfg.code_language == "bash"


def test_from_sphinx_config_code_classes_list_to_tuple() -> None:
    """Test that list code_classes are converted to tuple."""
    mock_config = types.SimpleNamespace(
        argparse_examples_code_classes=["highlight-console", "highlight-bash"],
    )
    cfg = ExemplarConfig.from_sphinx_config(mock_config)  # type: ignore[arg-type]

    assert isinstance(cfg.code_classes, tuple)
    assert cfg.code_classes == ("highlight-console", "highlight-bash")
