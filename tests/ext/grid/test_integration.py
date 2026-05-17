"""Integration tests for sphinx_ux_grid.

Builds a tiny MyST project that exercises every directive in the package
(``{grid}``, ``{grid-item-card}`` with both ``:link-type: doc`` and
``:link-type: url``) and asserts on the rendered HTML.
"""

from __future__ import annotations

import textwrap

import pytest

from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    extensions = [
        "myst_parser",
        "sphinx_ux_grid",
    ]
    myst_enable_extensions = ["colon_fence"]
    """,
)

_INDEX_MD = textwrap.dedent(
    """\
    # Demo

    ::::{grid} 1 2 3 4
    :gutter: 3
    :class-container: my-extra-grid

    :::{grid-item-card} Internal
    :link: page-two
    :link-type: doc

    Body text for the internal-link card.

    +++

    Footer text.
    :::

    :::{grid-item-card} External
    :link: https://example.com
    :link-type: url

    Body for the external-link card.
    :::

    ::::
    """,
)

_PAGE_TWO_MD = textwrap.dedent(
    """\
    # Page Two

    Second page content.
    """,
)


@pytest.fixture(scope="module")
def grid_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a minimal MyST project exercising every grid directive."""
    cache_root = tmp_path_factory.mktemp("grid-html")
    scenario = SphinxScenario(
        buildername="html",
        files=(
            ScenarioFile("conf.py", _CONF_PY),
            ScenarioFile("index.md", _INDEX_MD),
            ScenarioFile("page-two.md", _PAGE_TWO_MD),
        ),
    )
    return build_shared_sphinx_result(cache_root, scenario)


@pytest.mark.integration
def test_grid_container_renders_with_classes_and_style(
    grid_html_result: SharedSphinxResult,
) -> None:
    """The grid container carries gp-sphinx-grid* classes and inlined custom props."""
    html = read_output(grid_html_result, "index.html")
    assert "gp-sphinx-grid" in html
    # Class-container extension survives onto the container.
    assert "my-extra-grid" in html
    # Per-breakpoint column counts arrive as inline CSS custom properties.
    assert "--gp-sphinx-grid-cols-xs: 1" in html
    assert "--gp-sphinx-grid-cols-sm: 2" in html
    assert "--gp-sphinx-grid-cols-md: 3" in html
    assert "--gp-sphinx-grid-cols-lg: 4" in html
    # Gutter scale resolves to 1rem.
    assert "--gp-sphinx-grid-gutter: 1rem" in html


@pytest.mark.integration
def test_grid_item_card_link_doc_resolves_to_internal_href(
    grid_html_result: SharedSphinxResult,
) -> None:
    """``:link-type: doc`` resolves to the target docname's HTML URL."""
    html = read_output(grid_html_result, "index.html")
    # Card body classes are present.
    assert "gp-sphinx-grid-card" in html
    assert "gp-sphinx-grid-card__body" in html
    assert "gp-sphinx-grid-card__title" in html
    # Footer is present from the +++ split.
    assert "gp-sphinx-grid-card__footer" in html
    # The :link-type: doc resolves to an HTML href targeting page-two.
    assert "page-two.html" in html


@pytest.mark.integration
def test_grid_item_card_link_url_emits_external_href(
    grid_html_result: SharedSphinxResult,
) -> None:
    """``:link-type: url`` emits a plain external href on a reference node."""
    html = read_output(grid_html_result, "index.html")
    assert "https://example.com" in html


@pytest.mark.integration
def test_grid_directive_emits_no_design_classes(
    grid_html_result: SharedSphinxResult,
) -> None:
    """The package never emits the sphinx-design ``sd-`` classes."""
    html = read_output(grid_html_result, "index.html")
    # The grid container itself should not carry sd-grid-container or sd-row.
    grid_html_start = html.find('class="gp-sphinx-grid')
    assert grid_html_start != -1
    # Take a window around the grid and verify no sd- classes appear in it.
    window = html[grid_html_start : grid_html_start + 4000]
    assert "sd-grid-container" not in window
    assert "sd-row" not in window
    assert "sd-col" not in window
