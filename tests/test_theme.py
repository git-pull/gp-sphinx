"""Tests for gp_sphinx.theme module."""

from __future__ import annotations

from gp_sphinx.theme import get_theme_path


def test_theme_path_exists() -> None:
    """Theme directory exists."""
    assert get_theme_path().is_dir()


def test_theme_conf_exists() -> None:
    """Theme.conf is present."""
    assert (get_theme_path() / "theme.conf").is_file()


def test_theme_inherits_furo() -> None:
    """Theme inherits from furo."""
    conf = (get_theme_path() / "theme.conf").read_text()
    assert "inherit = furo" in conf


def test_theme_page_html_exists() -> None:
    """Page template is bundled."""
    assert (get_theme_path() / "page.html").is_file()


def test_theme_sidebar_brand_exists() -> None:
    """Brand sidebar template is bundled."""
    assert (get_theme_path() / "sidebar" / "brand.html").is_file()


def test_theme_sidebar_projects_exists() -> None:
    """Projects sidebar template is bundled."""
    assert (get_theme_path() / "sidebar" / "projects.html").is_file()


def test_theme_static_custom_css_exists() -> None:
    """Custom CSS is bundled in theme static."""
    assert (get_theme_path() / "static" / "css" / "custom.css").is_file()


def test_theme_static_spa_nav_js_exists() -> None:
    """SPA navigation JS is bundled in theme static."""
    assert (get_theme_path() / "static" / "js" / "spa-nav.js").is_file()
