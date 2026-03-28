"""Tests for gp_sphinx.ext.argparse module."""

from __future__ import annotations


def test_argparse_ext_importable() -> None:
    """Argparse extension module is importable."""
    from gp_sphinx.ext.argparse import setup

    assert callable(setup)


def test_argparse_roles_importable() -> None:
    """Argparse roles module is importable."""
    from gp_sphinx.ext.argparse import roles

    assert roles is not None


def test_argparse_lexer_importable() -> None:
    """Argparse lexer module is importable."""
    from gp_sphinx.ext.argparse.lexer import ArgparseLexer

    assert ArgparseLexer is not None


def test_cli_usage_lexer_importable() -> None:
    """CLI usage lexer module is importable."""
    from gp_sphinx.ext.argparse.cli_usage_lexer import CLIUsageLexer

    assert CLIUsageLexer is not None


def test_argparse_neo_package_exists() -> None:
    """Sphinx argparse neo package directory exists."""
    import importlib.util

    spec = importlib.util.find_spec("gp_sphinx.ext.argparse.neo")
    assert spec is not None


def test_highlight_css_exists() -> None:
    """Argparse highlight CSS file is bundled."""
    from gp_sphinx.ext.argparse import STATIC_DIR

    assert (STATIC_DIR / "highlight.css").is_file()


def test_theme_argparse_css_exists() -> None:
    """Argparse highlight CSS is also in theme static."""
    from gp_sphinx.theme import get_theme_path

    css = get_theme_path() / "static" / "css" / "argparse-highlight.css"
    assert css.is_file()
