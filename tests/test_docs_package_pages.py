"""Audit tests for package documentation page parity."""

from __future__ import annotations

import pathlib
import re
import textwrap

import pytest

from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    derive_sphinx_scenario_cache_root,
    read_output,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
PACKAGE_PAGES = sorted((DOCS_ROOT / "packages").glob("sphinx-autodoc-*.md"))
LIVE_DEMO_MARKERS = (
    "```{eval-rst}",
    "```{sab-badge-demo}",
    "```{autofixture-index}",
    ":::{auto-pytest-plugin}",
    "{tool}`",
    "{toolref}`",
)
_FASTMCP_DEMO_MODULE = (DOCS_ROOT / "_ext" / "fastmcp_demo_tools.py").read_text()
_FASTMCP_DOCS_PAGE = (DOCS_ROOT / "packages" / "sphinx-autodoc-fastmcp.md").read_text()
_FASTMCP_CONF = textwrap.dedent(
    f"""\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")
    sys.path.insert(0, r"{DOCS_ROOT / "_ext"}")
    sys.path.insert(
        0,
        r"{REPO_ROOT / "packages" / "sphinx-autodoc-fastmcp" / "src"}",
    )

    extensions = [
        "myst_parser",
        "sphinx_design",
        "package_reference",
        "sphinx_autodoc_fastmcp",
    ]

    root_doc = "api"
    master_doc = "api"
    fastmcp_tool_modules = ["fastmcp_demo_tools"]
    fastmcp_area_map = {{"fastmcp_demo_tools": "api"}}
    fastmcp_collector_mode = "introspect"
    """
)


def _section_content(text: str, heading: str) -> str:
    """Return the Markdown content under one second-level heading."""
    match = re.search(
        rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"Missing heading: ## {heading}"
    return match.group("body")


@pytest.mark.parametrize(
    "page_path",
    PACKAGE_PAGES,
    ids=[path.stem for path in PACKAGE_PAGES],
)
def test_autodoc_package_pages_have_copyable_examples_and_live_demos(
    page_path: pathlib.Path,
) -> None:
    """Each autodoc package page includes examples and rendered demos."""
    text = page_path.read_text()

    working_examples = _section_content(text, "Working usage examples")
    live_demos = _section_content(text, "Live demos")

    assert "```" in working_examples
    assert any(marker in live_demos for marker in LIVE_DEMO_MARKERS)
    assert "```{package-reference}" in text


def test_docs_conf_registers_fastmcp_demo_page_support() -> None:
    """The docs app loads FastMCP and the shared live demo module."""
    text = (DOCS_ROOT / "conf.py").read_text()

    assert '"sphinx_autodoc_fastmcp"' in text
    assert 'fastmcp_tool_modules=["fastmcp_demo_tools"]' in text
    assert '"packages/sphinx-autodoc-fastmcp"' in text


@pytest.fixture(scope="module")
def fastmcp_docs_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a cached FastMCP docs page scenario once for HTML assertions."""
    cache_root = derive_sphinx_scenario_cache_root(
        tmp_path_factory.mktemp("fastmcp-docs-page"),
    )
    scenario = SphinxScenario(
        files=(
            ScenarioFile("fastmcp_demo_tools.py", _FASTMCP_DEMO_MODULE),
            ScenarioFile(
                "conf.py",
                _FASTMCP_CONF.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile("api.md", _FASTMCP_DOCS_PAGE),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("fastmcp_demo_tools", "package_reference"),
    )


def test_fastmcp_docs_page_renders_live_demo_output(
    fastmcp_docs_result: SharedSphinxResult,
) -> None:
    """The FastMCP package page renders tool cards, refs, and summary output."""
    fastmcp_docs_html = read_output(fastmcp_docs_result, "api.html")

    assert 'class="smf-tool-section api-card-shell"' in fastmcp_docs_html
    assert (
        'class="api-entry api-card-entry api-profile--fastmcp-tool smf-tool-entry"'
        in fastmcp_docs_html
    )
    assert 'class="api-badge-container"' in fastmcp_docs_html
    assert "list_sessions" in fastmcp_docs_html
    assert "create_session" in fastmcp_docs_html
    assert "delete_session" in fastmcp_docs_html
    assert "Parameters" in fastmcp_docs_html
    assert "Inspect" in fastmcp_docs_html
    assert "Act" in fastmcp_docs_html
    assert "Destroy" in fastmcp_docs_html


# ---------------------------------------------------------------------------
# Narrative page tests (pure file-content, no Sphinx build)
# ---------------------------------------------------------------------------


def test_gallery_page_uses_live_eval_rst_demos() -> None:
    """Gallery page contains live eval-rst directives, not static ASCII art."""
    text = (DOCS_ROOT / "gallery.md").read_text()

    assert "```{eval-rst}" in text
    assert "autofunction::" in text or "autoclass::" in text
    assert "```{sab-badge-demo}" in text


def test_architecture_page_names_all_three_tiers() -> None:
    """Architecture page mentions all three tiers and key infrastructure packages."""
    text = (DOCS_ROOT / "architecture.md").read_text()

    assert "Shared infrastructure" in text or "Tier 1" in text
    assert "Domain" in text or "Tier 2" in text
    assert "Theme" in text or "Tier 3" in text or "Presentation" in text
    assert "sphinx-autodoc-layout" in text
    assert "sphinx-autodoc-badges" in text
    assert "sphinx-typehints-gp" in text


def test_whats_new_page_covers_key_advancements() -> None:
    """What's-new page documents the major branch advancements."""
    text = (DOCS_ROOT / "whats-new.md").read_text()

    assert "sphinx-autodoc-layout" in text
    assert "sphinx-typehints-gp" in text
    assert "badge" in text.lower()
    assert "9.5" in text


def test_homepage_has_six_cards() -> None:
    """Homepage grid contains at least six cards."""
    text = (DOCS_ROOT / "index.md").read_text()

    assert text.count("grid-item-card") >= 6
    assert "gallery" in text
    assert "architecture" in text
    assert "whats-new" in text


def test_homepage_says_twelve_packages() -> None:
    """Homepage references the correct package count."""
    text = (DOCS_ROOT / "index.md").read_text()

    assert "Twelve" in text or "twelve" in text or "12" in text


def test_quickstart_has_autodoc_demo() -> None:
    """Quickstart page includes an autodoc demo section."""
    text = (DOCS_ROOT / "quickstart.md").read_text()

    assert "autodoc" in text.lower() or "automodule" in text


def test_readme_uses_main_branch() -> None:
    """README references main branch, not master."""
    text = (REPO_ROOT / "README.md").read_text()

    assert "/blob/master/" not in text
