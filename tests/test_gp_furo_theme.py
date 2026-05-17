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
from gp_furo_theme import THEME_NAME, get_theme_path, get_vite_root, setup

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


def test_base_html_no_flicker_script_opts_out_of_rocket_loader() -> None:
    """Furo's body theme bootstrap carries ``data-cfasync="false"``.

    Furo's inline ``<script>document.body.dataset.theme =
    localStorage.getItem("theme") || "auto";</script>`` runs at the top
    of ``<body>`` to pre-set the theme attribute before any styled
    content paints. Under Cloudflare Rocket Loader the script is
    rewritten and deferred, so first paint can land in the wrong theme.
    The FOWT-prevention head script in
    ``packages/gp-sphinx/src/gp_sphinx/config.py:789-808`` is opted out
    for the same reason; this body script was missed. See
    ``config.py:730-755`` for the design rationale.
    """
    base = (get_theme_path() / "base.html").read_text()
    assert 'data-cfasync="false"' in base


def test_domainindex_collapse_index_script_opts_out_of_rocket_loader() -> None:
    """``COLLAPSE_INDEX`` setter carries ``data-cfasync="false"``.

    The Python ``genindex`` template injects
    ``<script>DOCUMENTATION_OPTIONS.COLLAPSE_INDEX = true</script>``
    when ``collapse_index`` is configured. Without an opt-out, Rocket
    Loader defers the assignment past the point where ``doctools.js``
    reads ``COLLAPSE_INDEX``, so the index renders expanded on first
    paint and re-collapses later. Opting out keeps the assignment
    synchronous in document order.
    """
    tpl = (get_theme_path() / "domainindex.html").read_text()
    assert 'data-cfasync="false"' in tpl


def test_setup_registers_theme() -> None:
    """setup() registers the theme + hooks + post-transform with Sphinx."""

    class FakeApp:
        def __init__(self) -> None:
            self.themes: list[tuple[str, str]] = []
            self.config_values: list[str] = []
            self.post_transforms: list[type] = []
            self.events: list[str] = []

        def require_sphinx(self, version: str) -> None:
            pass

        def add_config_value(self, name: str, **_: object) -> None:
            self.config_values.append(name)

        def add_html_theme(self, name: str, theme_path: str) -> None:
            self.themes.append((name, theme_path))

        def add_post_transform(self, transform: type) -> None:
            self.post_transforms.append(transform)

        def connect(self, event: str, _callback: object) -> None:
            self.events.append(event)

    app = FakeApp()
    metadata = setup(app)  # type: ignore[arg-type]
    assert app.themes == [(THEME_NAME, str(get_theme_path()))]
    assert "pygments_dark_style" in app.config_values
    assert sorted(app.events) == [
        "build-finished",
        "builder-inited",
        "html-page-context",
    ]
    assert len(app.post_transforms) == 1
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


def test_get_vite_root_returns_workspace_web_dir() -> None:
    """get_vite_root() resolves to gp-furo-theme/web/ from a workspace checkout."""
    root = get_vite_root()
    assert root is not None
    assert root.is_dir()
    assert (root / "package.json").is_file()
    assert (root / "vite.config.ts").is_file()


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
    expected_marker = "Ported from furo 2025.12.19 (b788b8a)"
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
def test_html_build_completes_with_gp_furo_theme(
    gp_furo_html_result: SharedSphinxResult,
) -> None:
    """A minimal Sphinx project builds successfully with html_theme = 'gp-furo'."""
    html = read_output(gp_furo_html_result, "index.html")
    assert "Demo" in html
    assert "Hello from the ported templates" in html


@pytest.mark.integration
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
