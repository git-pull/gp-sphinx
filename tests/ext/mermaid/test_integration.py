"""Integration tests: full Sphinx HTML build with a stubbed mmdc renderer.

The scenario ships a ``fake_mmdc.py`` stand-in for the real
``@mermaid-js/mermaid-cli`` binary: it honours the ``-i``/``-o``/``-c``
contract and bakes the config's ``themeVariables.primaryColor`` into the SVG,
so assertions can prove that both the light and the dark render config
actually reached the subprocess — without node, puppeteer, or Chrome.
"""

from __future__ import annotations

import re
import textwrap
import typing as t

import pytest

from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

pytestmark = pytest.mark.integration

_FAKE_MMDC = textwrap.dedent(
    '''\
    #!/usr/bin/env python3
    """Fake mmdc: writes a canned SVG shaped like real mermaid-cli output."""

    from __future__ import annotations

    import json
    import pathlib
    import sys


    def main() -> None:
        """Write the canned SVG to the ``-o`` path, filled per ``-c`` config."""
        args = sys.argv[1:]
        opts = {
            flag: args[index + 1]
            for index, flag in enumerate(args)
            if flag in {"-i", "-o", "-c", "-p", "-b"}
        }
        config = json.loads(pathlib.Path(opts["-c"]).read_text(encoding="utf-8"))
        fill = config["themeVariables"]["primaryColor"]
        svg = (
            '<svg id="my-svg" width="100%" '
            'style="max-width: 200px; background-color: transparent;" '
            'viewBox="0 0 200 80" role="graphics-document document">'
            "<style>#my-svg{fill:" + fill + ";}</style>"
            '<g class="node">a</g>'
            '<path marker-end="url(#my-svg_flowchart-pointEnd)"></path>'
            "</svg>"
        )
        pathlib.Path(opts["-o"]).write_text(svg, encoding="utf-8")


    if __name__ == "__main__":
        main()
    '''
)

# The exec bit is load-bearing: _resolve_mmdc tries shutil.which() on the
# configured path, and the scenario harness writes files without it. conf.py
# is the only scenario-owned code that runs before rendering, so it applies
# the chmod.
_CONF_PY = textwrap.dedent(
    """\
    import pathlib

    extensions = ["myst_parser", "sphinx_gp_mermaid"]
    html_theme = "basic"
    myst_enable_extensions = ["colon_fence"]
    myst_fence_as_directive = ["mermaid"]

    _stub = pathlib.Path(__file__).parent / "fake_mmdc.py"
    _stub.chmod(0o755)
    mermaid_cmd = str(_stub)
    """
)

_INDEX_MD = textwrap.dedent(
    """\
    # Demo

    ```mermaid
    flowchart LR
        a --> b
    ```

    :::{mermaid}
    :caption: How it flows.
    :alt: a to b
    :name: flow-diagram

    flowchart TD
        a --> b
    :::
    """
)


@pytest.fixture(scope="module")
def mermaid_html_build(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a MyST project rendering two diagrams through the stub mmdc."""
    cache_root = tmp_path_factory.mktemp("mermaid-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("conf.py", _CONF_PY),
            ScenarioFile("index.md", _INDEX_MD),
            ScenarioFile("fake_mmdc.py", _FAKE_MMDC),
        ),
    )
    return build_shared_sphinx_result(cache_root, scenario)


@pytest.fixture(scope="module")
def mermaid_html(mermaid_html_build: SharedSphinxResult) -> str:
    """Return the built ``index.html`` contents."""
    return read_output(mermaid_html_build, "index.html")


def test_build_does_not_degrade(
    mermaid_html_build: SharedSphinxResult,
    mermaid_html: str,
) -> None:
    """The stub renderer satisfies both renders; nothing falls back or warns.

    Cross-app registration noise ("already registered") is expected when many
    Sphinx apps share a process, so assert on the degradation signals only.
    """
    assert "mermaid render unavailable" not in mermaid_html_build.warnings
    assert "gp-sphinx-mermaid__fallback" not in mermaid_html


def test_both_fence_spellings_render_figures(mermaid_html: str) -> None:
    """The plain ```mermaid fence and :::{mermaid} both produce figures."""
    assert mermaid_html.count('<figure class="gp-sphinx-mermaid"') == 2


def test_dual_variants_carry_theme_fills(mermaid_html: str) -> None:
    """Each diagram inlines a light and a dark SVG from separate renders."""
    assert mermaid_html.count("gp-sphinx-mermaid__variant--theme-light") == 2
    assert mermaid_html.count("gp-sphinx-mermaid__variant--theme-dark") == 2
    # The stub bakes themeVariables.primaryColor into the fill, proving the
    # light and dark configs each flowed through the subprocess boundary.
    assert mermaid_html.count("fill:#f8f9fb;") == 2
    assert mermaid_html.count("fill:#1a1c1e;") == 2


def test_svgs_are_normalized(mermaid_html: str) -> None:
    """Ids are rewritten, size is explicit, and max-width is stripped."""
    assert "my-svg" not in mermaid_html
    assert len(re.findall(r'id="mermaid-[0-9a-f]{12}-light"', mermaid_html)) == 2
    assert len(re.findall(r'id="mermaid-[0-9a-f]{12}-dark"', mermaid_html)) == 2
    assert mermaid_html.count('width="200" height="80"') == 4
    assert "max-width" not in mermaid_html


def test_caption_alt_and_name_flow_through(mermaid_html: str) -> None:
    """Directive options surface as figcaption, aria-label, and figure id."""
    assert "<figcaption>How it flows.</figcaption>" in mermaid_html
    assert 'aria-label="a to b"' in mermaid_html
    assert 'id="flow-diagram"' in mermaid_html
    assert mermaid_html.count('aria-hidden="true"') == 2


def test_stylesheet_ships_with_the_package(
    mermaid_html_build: SharedSphinxResult,
    mermaid_html: str,
) -> None:
    """The packaged CSS is linked in the page and copied into _static."""
    assert "css/sphinx_gp_mermaid.css" in mermaid_html
    css = mermaid_html_build.outdir / "_static" / "css" / "sphinx_gp_mermaid.css"
    assert css.is_file()


def test_cache_dir_is_excluded_and_populated(
    mermaid_html_build: SharedSphinxResult,
) -> None:
    """The confdir cache holds one SVG per (diagram, theme) and is excluded."""
    assert "_mermaid_cache" in mermaid_html_build.app.config.exclude_patterns
    cache = mermaid_html_build.srcdir / "_mermaid_cache"
    assert len(list(cache.glob("*.svg"))) == 4


def test_figure_markup_snapshot(
    mermaid_html: str,
    snapshot_html_fragment: t.Callable[..., None],
) -> None:
    """The named figure's full markup is stable across runs."""
    match = re.search(
        r'<figure class="gp-sphinx-mermaid" id="flow-diagram">.*?</figure>',
        mermaid_html,
        flags=re.DOTALL,
    )
    assert match is not None
    snapshot_html_fragment(match.group(0))
