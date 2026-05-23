"""Integration tests for ``{octicon}`` role rendering.

Verifies that the HTML builder emits the SVG payload without leaking the
icon-name fallback text, and that the text builder renders the icon name
instead of raw SVG markup.
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
        "sphinx_ux_octicons",
    ]
    """
)

_INDEX_MD = textwrap.dedent(
    """\
    # Demo

    Inline: {octicon}`rocket` here.
    """
)


@pytest.fixture(scope="module")
def octicons_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a minimal MyST project with the ``{octicon}`` role (HTML builder)."""
    cache_root = tmp_path_factory.mktemp("octicons-html")
    scenario = SphinxScenario(
        buildername="html",
        files=(
            ScenarioFile("conf.py", _CONF_PY),
            ScenarioFile("index.md", _INDEX_MD),
        ),
    )
    return build_shared_sphinx_result(cache_root, scenario)


@pytest.fixture(scope="module")
def octicons_text_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a minimal MyST project with the ``{octicon}`` role (text builder)."""
    cache_root = tmp_path_factory.mktemp("octicons-text")
    scenario = SphinxScenario(
        buildername="text",
        files=(
            ScenarioFile("conf.py", _CONF_PY),
            ScenarioFile("index.md", _INDEX_MD),
        ),
    )
    return build_shared_sphinx_result(cache_root, scenario)


@pytest.mark.integration
def test_html_emits_svg_without_icon_name_leak(
    octicons_html_result: SharedSphinxResult,
) -> None:
    """HTML output contains the SVG and never the trailing-name leak."""
    html = read_output(octicons_html_result, "index.html")

    # Exactly one rendered SVG element with the expected class pair.
    svg_open = '<svg xmlns="http://www.w3.org/2000/svg"'
    assert html.count(svg_open) == 1
    assert 'class="gp-sphinx-octicon gp-sphinx-octicon--rocket"' in html

    # The icon-name fallback text must not leak into HTML output after
    # the SVG payload.
    assert "</svg>rocket" not in html
    # Alternate framing in case the leak is wrapped in another tag.
    assert ">rocket<" not in html.split("</svg>", 1)[1][:32]


@pytest.mark.integration
def test_text_builder_renders_icon_name_fallback(
    octicons_text_result: SharedSphinxResult,
) -> None:
    """Text builder renders the icon name as the visible surrogate."""
    text = read_output(octicons_text_result, "index.txt")
    # The icon name is the visible surrogate carried as a Text child for
    # builders other than HTML.
    assert "rocket" in text
    # The text builder must not emit raw SVG markup.
    assert "<svg" not in text
