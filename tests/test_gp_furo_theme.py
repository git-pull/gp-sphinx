"""Smoke tests for gp_furo_theme package skeleton.

Template, asset, and behavior tests land in subsequent steps as those
surfaces are populated. This file only proves the skeleton is wired up:
the package imports, the theme directory exists with a minimal
``theme.conf``, ``setup()`` registers ``gp-furo`` against Sphinx, and the
entry point is discoverable.
"""

from __future__ import annotations

import importlib.metadata
import pathlib
import typing as t

from gp_furo_theme import THEME_NAME, get_theme_path, setup

if t.TYPE_CHECKING:
    pass


def test_theme_path_exists() -> None:
    """Theme directory is bundled in the package."""
    assert get_theme_path().is_dir()


def test_theme_conf_exists() -> None:
    """theme.conf is present at the canonical location."""
    assert (get_theme_path() / "theme.conf").is_file()


def test_theme_conf_inherits_basic_ng() -> None:
    """Theme inherits from basic-ng (Sphinx 6+ improved basic theme)."""
    conf = (get_theme_path() / "theme.conf").read_text()
    assert "inherit = basic-ng" in conf


def test_theme_conf_does_not_inherit_furo() -> None:
    """Theme has cut its dependency on upstream furo."""
    conf = (get_theme_path() / "theme.conf").read_text()
    assert "inherit = furo" not in conf


def test_theme_conf_declares_furo_options() -> None:
    """Public option surface mirrors upstream Furo's theme.conf."""
    conf = (get_theme_path() / "theme.conf").read_text()
    for option in (
        "announcement",
        "dark_css_variables",
        "light_css_variables",
        "dark_logo",
        "light_logo",
        "footer_icons",
        "top_of_page_button",
        "source_repository",
        "source_branch",
        "source_directory",
        "source_edit_link",
        "source_view_link",
    ):
        assert option in conf, f"theme.conf is missing the {option!r} option"


def test_setup_registers_theme() -> None:
    """setup() calls add_html_theme with the theme name and path."""

    class FakeApp:
        def __init__(self) -> None:
            self.themes: list[tuple[str, pathlib.Path]] = []

        def add_html_theme(self, name: str, theme_path: pathlib.Path) -> None:
            self.themes.append((name, theme_path))

    app = FakeApp()
    metadata = setup(app)  # type: ignore[arg-type]
    assert app.themes == [(THEME_NAME, get_theme_path())]
    assert metadata["parallel_read_safe"] is True
    assert metadata["parallel_write_safe"] is True


def test_theme_name_is_gp_furo() -> None:
    """Theme registers under the canonical name 'gp-furo'."""
    assert THEME_NAME == "gp-furo"


def test_entry_point_is_discoverable() -> None:
    """The sphinx.html_themes entry point is discoverable via importlib.metadata."""
    eps = importlib.metadata.entry_points(group="sphinx.html_themes")
    matched = [ep for ep in eps if ep.name == "gp-furo"]
    assert matched, "gp-furo entry point not discoverable"
    assert matched[0].value == "gp_furo_theme"


def test_license_furo_present() -> None:
    """LICENSE-FURO file is checked in at the package root."""
    package_root = pathlib.Path(__file__).parents[1] / "packages" / "gp-furo-theme"
    assert (package_root / "LICENSE-FURO").is_file()
