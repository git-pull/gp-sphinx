"""Tests for the docs package reference helpers."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "docs" / "_ext"))

import package_reference

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_workspace_packages_lists_publishable_packages() -> None:
    """Workspace package discovery includes every published package."""
    names = {package["name"] for package in package_reference.workspace_packages()}
    assert names == {
        "gp-sphinx",
        "sphinx-argparse-neo",
        "sphinx-autodoc-docutils",
        "sphinx-autodoc-pytest-fixtures",
        "sphinx-autodoc-sphinx",
        "sphinx-fonts",
        "sphinx-gptheme",
    }


def test_collect_extension_surface_for_sphinx_fonts() -> None:
    """The surface collector captures live config registration."""
    surface = package_reference.collect_extension_surface("sphinx_fonts")
    config_names = {item["name"] for item in surface["config_values"]}
    assert config_names == {
        "sphinx_fonts",
        "sphinx_font_fallbacks",
        "sphinx_font_css_variables",
        "sphinx_font_preload",
    }


def test_package_reference_markdown_for_argparse_includes_roles() -> None:
    """Generated markdown includes the exemplar role registrations."""
    markdown = package_reference.package_reference_markdown("sphinx-argparse-neo")
    assert "cli-option" in markdown
    assert "argparse_examples_section_title" in markdown


def test_package_reference_markdown_for_docutils_includes_directives() -> None:
    """Generated markdown includes registered docutils autodoc directives."""
    markdown = package_reference.package_reference_markdown("sphinx-autodoc-docutils")
    assert "autodirective" in markdown
    assert "autorole-index" in markdown


def test_package_reference_markdown_uses_plain_config_heading() -> None:
    """Generated markdown avoids headings that become accidental autolinks."""
    markdown = package_reference.package_reference_markdown("sphinx-fonts")
    assert "## Copyable config snippet" in markdown


def test_docs_package_pages_exist_for_every_workspace_package() -> None:
    """Each publishable package has a matching docs page."""
    page_names = {
        path.stem
        for path in (REPO_ROOT / "docs" / "packages").glob("*.md")
        if path.stem != "index"
    }
    package_names = {
        package["name"] for package in package_reference.workspace_packages()
    }
    assert page_names == package_names


def test_package_reference_markdown_unknown_package_returns_empty() -> None:
    """Unknown package names return an empty string rather than crashing."""
    result = package_reference.package_reference_markdown("nonexistent-package")
    assert result == ""


def test_redirects_cover_legacy_extensions_paths() -> None:
    """Legacy extensions/* redirects exist for the packages index and pages."""
    redirects = (REPO_ROOT / "docs" / "redirects.txt").read_text().splitlines()
    redirect_map = dict(line.split(maxsplit=1) for line in redirects if line.strip())
    expected = {
        "extensions/index": "packages/index",
        **{
            f"extensions/{package['name']}": f"packages/{package['name']}"
            for package in package_reference.workspace_packages()
        },
    }
    assert redirect_map == expected
