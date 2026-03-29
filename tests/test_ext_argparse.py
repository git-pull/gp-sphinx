"""Tests for sphinx_argparse_neo package."""

from __future__ import annotations


def test_argparse_neo_importable() -> None:
    """Argparse neo extension module is importable."""
    from sphinx_argparse_neo import setup

    assert callable(setup)


def test_argparse_roles_importable() -> None:
    """Argparse roles module is importable."""
    from sphinx_argparse_neo import roles

    assert roles is not None


def test_argparse_lexer_importable() -> None:
    """Argparse lexer module is importable."""
    from sphinx_argparse_neo.lexer import ArgparseLexer

    assert ArgparseLexer is not None


def test_cli_usage_lexer_importable() -> None:
    """CLI usage lexer module is importable."""
    from sphinx_argparse_neo.cli_usage_lexer import CLIUsageLexer

    assert CLIUsageLexer is not None


def test_highlight_css_exists() -> None:
    """Argparse highlight CSS file is bundled."""
    import pathlib

    from sphinx_argparse_neo import __file__ as neo_file

    css_path = pathlib.Path(neo_file).parent / "highlight.css"
    assert css_path.is_file()


def test_theme_argparse_css_exists() -> None:
    """Argparse highlight CSS is also in theme static."""
    from sphinx_gptheme import get_theme_path

    css = get_theme_path() / "static" / "css" / "argparse-highlight.css"
    assert css.is_file()
