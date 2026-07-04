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


def _autodoc_and_ux_package_paths() -> list[pathlib.Path]:
    """Return one docs page per autodoc, ux, or gp package.

    Accepts both layouts during the per-package migration window:
    ``docs/packages/<name>.md`` (legacy flat) and
    ``docs/packages/<name>/examples.md`` (post-migration). The
    examples.md subpage is where live-demo content moves once the
    package has migrated.
    """
    packages_dir = DOCS_ROOT / "packages"
    paths: list[pathlib.Path] = []
    candidates = sorted(
        {
            p.parent.name if p.parent.name != "packages" else p.stem
            for p in [
                *packages_dir.glob("sphinx-autodoc-*.md"),
                *packages_dir.glob("sphinx-ux-*.md"),
                *packages_dir.glob("sphinx-gp-*.md"),
                *packages_dir.glob("sphinx-autodoc-*/index.md"),
                *packages_dir.glob("sphinx-ux-*/index.md"),
                *packages_dir.glob("sphinx-gp-*/index.md"),
            ]
        }
    )
    for name in candidates:
        flat = packages_dir / f"{name}.md"
        examples = packages_dir / name / "examples.md"
        if examples.is_file():
            paths.append(examples)
        elif flat.is_file():
            paths.append(flat)
    return paths


PACKAGE_PAGES = _autodoc_and_ux_package_paths()
LIVE_DEMO_MARKERS = (
    "```{eval-rst}",
    "```{gp-sphinx-badge-demo}",
    ":::{auto-pytest-plugin}",
    "```{argparse}",
    "{tool}`",
    "{toolref}`",
    "```{mermaid-examples}",
)


def _fastmcp_docs_page() -> str:
    """Return the FastMCP examples / demos page contents.

    Prefers ``packages/sphinx-autodoc-fastmcp/examples.md`` (post-E7
    migration); falls back to the flat legacy page until the
    migration lands.
    """
    examples = DOCS_ROOT / "packages" / "sphinx-autodoc-fastmcp" / "examples.md"
    flat = DOCS_ROOT / "packages" / "sphinx-autodoc-fastmcp.md"
    return examples.read_text() if examples.is_file() else flat.read_text()


_FASTMCP_DEMO_MODULE = (DOCS_ROOT / "_ext" / "fastmcp_demo_tools.py").read_text()
_FASTMCP_DOCS_PAGE = _fastmcp_docs_page()
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
        "sphinx.ext.autodoc",
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


def _test_id_for(path: pathlib.Path) -> str:
    """Stable test ID across legacy + per-package layouts."""
    if path.name == "examples.md":
        return path.parent.name
    return path.stem


@pytest.mark.parametrize(
    "page_path",
    PACKAGE_PAGES,
    ids=[_test_id_for(path) for path in PACKAGE_PAGES],
)
def test_autodoc_package_pages_have_copyable_examples_and_live_demos(
    page_path: pathlib.Path,
) -> None:
    """Each autodoc package page exposes live demos.

    Pre-migration: a flat ``packages/<name>.md`` page carried both
    ``## Working usage examples`` and ``## Live demos`` H2 sections.
    Post-migration: those H2 sections live on per-package subpages
    (``packages/<name>/{tutorial,examples}.md``); for migrated
    packages we assert the ``examples.md`` subpage carries one of
    the live-demo markers, and skip the H2 / package-reference
    checks (those live on the landing now).
    """
    text = page_path.read_text()

    if page_path.name == "examples.md":
        # Migrated package: examples.md must carry at least one live
        # demo marker; the package-reference and section structure
        # are owned by the landing.
        assert any(marker in text for marker in LIVE_DEMO_MARKERS), (
            f"{page_path.relative_to(REPO_ROOT)} missing live demo marker"
        )
        return

    # Legacy flat page: assert the original three structural pieces.
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
    # Post-E7: fastmcp_area_map points at the per-package examples
    # subpage where the live demos render. Pre-migration accepts the
    # legacy flat-page docname.
    assert (
        '"packages/sphinx-autodoc-fastmcp/examples"' in text
        or '"packages/sphinx-autodoc-fastmcp"' in text
    )


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

    assert (
        'class="gp-sphinx-fastmcp__tool-section gp-sphinx-api-card-shell"'
        in fastmcp_docs_html
    )
    expected_tool_entry_classes = (
        'class="gp-sphinx-api-entry gp-sphinx-api-card-entry'
        " gp-sphinx-api-profile--fastmcp-tool"
        ' gp-sphinx-fastmcp__tool-entry"'
    )
    assert expected_tool_entry_classes in fastmcp_docs_html
    assert 'class="gp-sphinx-api-badge-container"' in fastmcp_docs_html
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
    assert "```{gp-sphinx-badge-demo}" in text


def test_architecture_page_names_all_three_tiers() -> None:
    """Architecture page mentions all three tiers and key infrastructure packages."""
    text = (DOCS_ROOT / "architecture.md").read_text()

    assert "Shared infrastructure" in text or "Tier 1" in text
    assert "Domain" in text or "Tier 2" in text
    assert "Theme" in text or "Tier 3" in text or "Presentation" in text
    assert "sphinx-ux-autodoc-layout" in text
    assert "sphinx-ux-badges" in text
    assert "sphinx-autodoc-typehints-gp" in text


def test_whats_new_page_covers_key_advancements() -> None:
    """What's-new page documents the major branch advancements."""
    text = (DOCS_ROOT / "whats-new.md").read_text()

    assert "sphinx-ux-autodoc-layout" in text
    assert "sphinx-autodoc-typehints-gp" in text
    assert "badge" in text.lower()
    assert "9.5" in text


def test_homepage_has_six_cards() -> None:
    """Homepage grid contains at least six cards."""
    text = (DOCS_ROOT / "index.md").read_text()

    assert text.count("grid-item-card") >= 6
    assert "gallery" in text
    assert "architecture" in text
    assert "whats-new" in text


def test_homepage_packages_card_uses_drift_proof_phrasing() -> None:
    """Homepage Packages card references the package families, not a raw count.

    Workspace package counts drift every time a new package lands. The
    homepage card SHOULD describe the *families* (autodoc extensions,
    build utils, UX, theme, …) so it stays accurate as the workspace
    grows. This test guards against re-introducing a hardcoded count
    like "Twelve workspace packages …".
    """
    text = (DOCS_ROOT / "index.md").read_text()

    forbidden_count_words = (
        "Two ",
        "Three ",
        "Four ",
        "Five ",
        "Six ",
        "Seven ",
        "Eight ",
        "Nine ",
        "Ten ",
        "Eleven ",
        "Twelve ",
        "Thirteen ",
        "Fourteen ",
        "Fifteen ",
        "Sixteen ",
        "Seventeen ",
        "Eighteen ",
        "Nineteen ",
        "Twenty ",
    )
    for word in forbidden_count_words:
        assert f"{word}workspace" not in text, (
            f"homepage uses hardcoded count {word.strip()!r} — drift-prone; "
            "describe package families instead"
        )
        assert f"{word}package" not in text, (
            f"homepage uses hardcoded count {word.strip()!r} — drift-prone; "
            "describe package families instead"
        )

    # The card itself must still exist and link to the packages index.
    assert "packages/index" in text
    assert "grid-item-card} Packages" in text


def test_quickstart_has_autodoc_demo() -> None:
    """Quickstart page includes an autodoc demo section."""
    text = (DOCS_ROOT / "quickstart.md").read_text()

    assert "autodoc" in text.lower() or "automodule" in text


def test_readme_uses_main_branch() -> None:
    """README references main branch, not master."""
    text = (REPO_ROOT / "README.md").read_text()

    assert "/blob/master/" not in text
