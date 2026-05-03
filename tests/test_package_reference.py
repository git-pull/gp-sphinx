"""Tests for the docs package reference helpers."""

from __future__ import annotations

import pathlib
import sys
import typing as t

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "docs" / "_ext"))

import package_reference

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_workspace_packages_lists_publishable_packages() -> None:
    """Workspace package discovery includes every published package."""
    names = {package["name"] for package in package_reference.workspace_packages()}
    assert names == {
        "gp-furo-theme",
        "sphinx-gp-opengraph",
        "sphinx-gp-sitemap",
        "gp-sphinx",
        "sphinx-autodoc-argparse",
        "sphinx-autodoc-api-style",
        "sphinx-ux-badges",
        "sphinx-autodoc-docutils",
        "sphinx-autodoc-fastmcp",
        "sphinx-ux-autodoc-layout",
        "sphinx-autodoc-typehints-gp",
        "sphinx-autodoc-pytest-fixtures",
        "sphinx-autodoc-sphinx",
        "sphinx-fonts",
        "sphinx-gp-theme",
        "sphinx-vite-builder",
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


def test_package_reference_markdown_emits_conf_snippet_for_argparse() -> None:
    """Conf snippet wires the package's importable module name."""
    markdown = package_reference.package_reference_markdown("sphinx-autodoc-argparse")
    assert '"sphinx_autodoc_argparse"' in markdown
    assert "## Copyable config snippet" in markdown


def test_package_reference_markdown_emits_conf_snippet_for_docutils() -> None:
    """Conf snippet wires the package's importable module name."""
    markdown = package_reference.package_reference_markdown("sphinx-autodoc-docutils")
    assert '"sphinx_autodoc_docutils"' in markdown
    assert "## Copyable config snippet" in markdown


def test_package_reference_markdown_uses_plain_config_heading() -> None:
    """Generated markdown avoids headings that become accidental autolinks."""
    markdown = package_reference.package_reference_markdown("sphinx-fonts")
    assert "## Copyable config snippet" in markdown


def test_package_reference_markdown_omits_surface_tables() -> None:
    """Surface documentation is owned by autoconfigvalue / autodirective directives."""
    markdown = package_reference.package_reference_markdown("sphinx-autodoc-fastmcp")
    assert "Registered Surface" not in markdown
    assert "#### Config values" not in markdown
    assert "#### Directives" not in markdown
    assert "#### Roles" not in markdown


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
    assert package_names <= page_names, (
        f"Missing docs pages for packages: {package_names - page_names}"
    )


def test_extension_modules_skips_unimportable_module() -> None:
    """An ImportError during module import returns [] instead of crashing."""
    result = package_reference.extension_modules("_this_module_does_not_exist_")
    assert result == []


def test_collect_extension_surface_skips_unimportable_module() -> None:
    """An ImportError in collect_extension_surface returns an empty SurfaceDict."""
    surface = package_reference.collect_extension_surface(
        "_this_module_does_not_exist_",
    )
    assert surface["module"] == "_this_module_does_not_exist_"
    assert surface["config_values"] == []
    assert surface["directives"] == []


def test_extract_arg_returns_positional_first() -> None:
    """The helper prefers positional args; kwargs are the fallback."""
    assert package_reference._extract_arg(0, "name", ("foo",), {}) == "foo"
    assert package_reference._extract_arg(0, "name", ("foo",), {"name": "bar"}) == "foo"


def test_extract_arg_falls_back_to_kwargs() -> None:
    """The helper picks the kwarg when the positional slot is empty.

    Regression guard: Sphinx APIs accept both ``app.add_directive("foo", Foo)``
    AND ``app.add_directive(name="foo", cls=Foo)``. A consumer that only
    indexes ``args[N]`` raises ``IndexError`` (or silently misses the
    registration) on the keyword form.
    """
    assert package_reference._extract_arg(0, "name", (), {"name": "foo"}) == "foo"
    assert package_reference._extract_arg(1, "cls", (), {"cls": object}) is object


def test_extract_arg_missing_returns_none() -> None:
    """Neither positional nor kwarg present yields None for the caller to skip."""
    assert package_reference._extract_arg(0, "name", (), {}) is None
    assert package_reference._extract_arg(2, "cls", ("foo", object), {}) is None


def test_package_reference_markdown_unknown_package_returns_empty() -> None:
    """Unknown package names return an empty string rather than crashing."""
    result = package_reference.package_reference_markdown("nonexistent-package")
    assert result == ""


def test_redirects_cover_legacy_extensions_paths() -> None:
    """Legacy extensions/* redirects exist for the packages index and pages."""
    redirects = (REPO_ROOT / "docs" / "redirects.txt").read_text().splitlines()
    redirect_map = dict(line.split(maxsplit=1) for line in redirects if line.strip())
    required = {
        "extensions/index": "packages/index",
        **{
            f"extensions/{package['name']}": f"packages/{package['name']}"
            for package in package_reference.workspace_packages()
        },
    }
    # Required entries must be present; additional backward-compat redirects
    # (e.g., packages/sphinx-gptheme -> packages/sphinx-gp-theme) are allowed.
    missing = required.keys() - redirect_map.keys()
    assert not missing, f"Missing redirects: {missing}"
    for source, target in required.items():
        assert redirect_map[source] == target, (
            f"Redirect {source!r} points to {redirect_map[source]!r}, "
            f"expected {target!r}"
        )


class MaturityBadgeFixture(t.NamedTuple):
    """Fixture for maturity_badge() input/output pairs."""

    test_id: str
    maturity: str
    expected: str


MATURITY_BADGE_FIXTURES: list[MaturityBadgeFixture] = [
    MaturityBadgeFixture(
        test_id="alpha",
        maturity="Alpha",
        expected="{bdg-warning-line}`Alpha`",
    ),
    MaturityBadgeFixture(
        test_id="beta",
        maturity="Beta",
        expected="{bdg-success-line}`Beta`",
    ),
    MaturityBadgeFixture(
        test_id="unknown_falls_back_to_secondary",
        maturity="Stable",
        expected="{bdg-secondary-line}`Stable`",
    ),
]


@pytest.mark.parametrize(
    list(MaturityBadgeFixture._fields),
    MATURITY_BADGE_FIXTURES,
    ids=[f.test_id for f in MATURITY_BADGE_FIXTURES],
)
def test_maturity_badge(test_id: str, maturity: str, expected: str) -> None:
    """maturity_badge() returns the correct sphinx-design badge role."""
    assert package_reference.maturity_badge(maturity) == expected


class GridMarkdownFixture(t.NamedTuple):
    """Fixture for workspace_package_grid_markdown() structural checks."""

    test_id: str
    substring: str
    present: bool


GRID_MARKDOWN_FIXTURES: list[GridMarkdownFixture] = [
    GridMarkdownFixture(
        test_id="has_grid_directive",
        substring="::::{grid} 1 1 2 2",
        present=True,
    ),
    GridMarkdownFixture(
        test_id="has_card_footer_separator",
        substring="+++",
        present=True,
    ),
    GridMarkdownFixture(
        test_id="maturity_badge_present_somewhere_in_output",
        substring="{bdg-",
        present=True,
    ),
]


@pytest.mark.parametrize(
    list(GridMarkdownFixture._fields),
    GRID_MARKDOWN_FIXTURES,
    ids=[f.test_id for f in GRID_MARKDOWN_FIXTURES],
)
def test_workspace_package_grid_markdown_structure(
    test_id: str,
    substring: str,
    present: bool,
) -> None:
    """Grid markdown output has the expected structural properties."""
    output = package_reference.workspace_package_grid_markdown()
    assert (substring in output) == present


class DomainRegistrationFixture(t.NamedTuple):
    """Expected py-domain registration from _register_extension_objects."""

    test_id: str
    full_name: str
    expected_objtype: str
    expected_docname: str


DOMAIN_REGISTRATION_FIXTURES: list[DomainRegistrationFixture] = [
    DomainRegistrationFixture(
        test_id="autodirective_class",
        full_name="sphinx_autodoc_docutils._directives.AutoDirective",
        expected_objtype="class",
        expected_docname="packages/sphinx-autodoc-docutils",
    ),
    DomainRegistrationFixture(
        test_id="autorole_class",
        full_name="sphinx_autodoc_docutils._directives.AutoRole",
        expected_objtype="class",
        expected_docname="packages/sphinx-autodoc-docutils",
    ),
    DomainRegistrationFixture(
        test_id="sphinx_autoconfigvalue_class",
        full_name="sphinx_autodoc_sphinx._directives.AutoconfigvalueDirective",
        expected_objtype="class",
        expected_docname="packages/sphinx-autodoc-sphinx",
    ),
    DomainRegistrationFixture(
        test_id="exemplar_role_from_submodule",
        full_name="sphinx_autodoc_argparse.roles.cli_option_role",
        expected_objtype="function",
        expected_docname="packages/sphinx-autodoc-argparse",
    ),
]


@pytest.mark.parametrize(
    list(DomainRegistrationFixture._fields),
    DOMAIN_REGISTRATION_FIXTURES,
    ids=[f.test_id for f in DOMAIN_REGISTRATION_FIXTURES],
)
def test_register_extension_objects_populates_py_domain(
    test_id: str,
    full_name: str,
    expected_objtype: str,
    expected_docname: str,
) -> None:
    """_register_extension_objects writes extension classes into the py domain dict."""

    class _MockPyDomain:
        objects: t.ClassVar[dict[str, t.Any]] = {}

    class _MockEnv:
        domains: t.ClassVar[dict[str, object]] = {"py": _MockPyDomain()}

    package_reference._register_extension_objects(None, _MockEnv())

    assert full_name in _MockPyDomain.objects, f"{full_name!r} not registered"
    entry = _MockPyDomain.objects[full_name]
    assert entry.objtype == expected_objtype
    assert entry.docname == expected_docname


def test_workspace_package_grid_markdown_badge_not_in_card_titles() -> None:
    """Maturity badges appear in the card footer, not in card title lines."""
    output = package_reference.workspace_package_grid_markdown()
    title_lines = [
        line for line in output.splitlines() if line.startswith(":::{grid-item-card}")
    ]
    assert title_lines, "expected at least one card title line"
    for line in title_lines:
        assert "{bdg-" not in line, f"badge found in card title: {line!r}"
