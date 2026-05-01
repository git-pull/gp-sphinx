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
import textwrap
import typing as t

import pytest
from gp_furo_theme import THEME_NAME, get_theme_path, setup

from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

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


_EXPECTED_TEMPLATE_PATHS = (
    "base.html",
    "components/edit-this-page.html",
    "components/view-this-page.html",
    "domainindex.html",
    "genindex.html",
    "globaltoc.html",
    "layout.html",
    "localtoc.html",
    "page.html",
    "partials/_head_css_variables.html",
    "partials/icons.html",
    "search.html",
    "sidebar/brand.html",
    "sidebar/ethical-ads.html",
    "sidebar/navigation.html",
    "sidebar/rtd-versions.html",
    "sidebar/scroll-end.html",
    "sidebar/scroll-start.html",
    "sidebar/search.html",
    "sidebar/variant-selector.html",
)


def test_all_furo_templates_are_ported() -> None:
    """Every Furo template exists in the gp-furo theme directory."""
    theme_root = get_theme_path()
    missing = [
        rel for rel in _EXPECTED_TEMPLATE_PATHS if not (theme_root / rel).is_file()
    ]
    assert not missing, f"templates missing: {missing}"


def test_ported_templates_carry_attribution_header() -> None:
    """Every ported template begins with the upstream-attribution comment."""
    theme_root = get_theme_path()
    expected_marker = "Ported from furo @ 752bf80c"
    missing_attribution = []
    for rel in _EXPECTED_TEMPLATE_PATHS:
        first_line = (theme_root / rel).read_text().splitlines()[0]
        if expected_marker not in first_line:
            missing_attribution.append(rel)
    assert not missing_attribution, (
        f"templates missing attribution header: {missing_attribution}"
    )


_GP_FURO_CONF = textwrap.dedent(
    """\
    extensions = ["gp_furo_theme"]
    html_theme = "gp-furo"
    master_doc = "index"
    project = "gp-furo demo"
    """,
)

_GP_FURO_INDEX = textwrap.dedent(
    """\
    Demo
    ====

    Hello from the ported templates.
    """,
)


@pytest.fixture(scope="module")
def gp_furo_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a minimal Sphinx HTML project using the gp-furo theme.

    Will start working in step 4, once ``_html_page_context`` lands and
    populates the ``furo_pygments`` / navigation / hide-toc Jinja context
    variables the ported templates expect.
    """
    cache_root = tmp_path_factory.mktemp("gp-furo-theme-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("conf.py", _GP_FURO_CONF),
            ScenarioFile("index.rst", _GP_FURO_INDEX),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("gp_furo_theme",),
    )


@pytest.mark.integration
@pytest.mark.xfail(
    reason="Templates expect furo_pygments / nav-tree context variables; "
    "_html_page_context port lands in step 4.",
    strict=True,
)
def test_html_build_completes_with_gp_furo_theme(
    gp_furo_html_result: SharedSphinxResult,
) -> None:
    """A minimal Sphinx project builds successfully with html_theme = 'gp-furo'."""
    html = read_output(gp_furo_html_result, "index.html")
    assert "Demo" in html
    assert "Hello from the ported templates" in html


@pytest.mark.integration
@pytest.mark.xfail(
    reason=(
        "Same template-context dependency as build-completes test; "
        "lands in step 4."
    ),
    strict=True,
)
def test_html_build_emits_no_template_warnings(
    gp_furo_html_result: SharedSphinxResult,
) -> None:
    """gp-furo template port produces no Sphinx warnings about missing partials."""
    warnings = gp_furo_html_result.warnings
    template_warnings = [
        line
        for line in warnings.splitlines()
        if "template" in line.lower() or "no theme" in line.lower()
    ]
    assert not template_warnings, f"unexpected template warnings: {template_warnings}"
