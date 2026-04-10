"""Integration tests for sphinx_autodoc_fastmcp shared layout cards."""

from __future__ import annotations

import textwrap

import pytest

from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

_MODULE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations

    import types


    def list_sessions(server: str, limit: int = 20) -> str:
        \"\"\"List sessions for one server.

        Parameters
        ----------
        server : str
            Server name.
        limit : int
            Maximum number of sessions to return.
        \"\"\"

        return "[]"


    list_sessions.__fastmcp__ = types.SimpleNamespace(
        name="list_sessions",
        title="List Sessions",
        tags={"readonly"},
        annotations=None,
    )
    """
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx_autodoc_fastmcp",
    ]

    fastmcp_tool_modules = ["demo_tools"]
    fastmcp_area_map = {"demo_tools": "api"}
    fastmcp_collector_mode = "introspect"
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Tools
    =====

    Use :toolref:`list_sessions` for an inline link.

    .. fastmcp-tool:: demo_tools.list_sessions

    .. fastmcp-tool-input:: demo_tools.list_sessions
    """
)


@pytest.fixture(scope="module")
def fastmcp_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    cache_root = tmp_path_factory.mktemp("fastmcp-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("demo_tools.py", _MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _CONF_PY.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _INDEX_RST),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("demo_tools",),
    )


@pytest.mark.integration
def test_fastmcp_tool_cards_use_shared_layout(
    fastmcp_html_result: SharedSphinxResult,
) -> None:
    html = read_output(fastmcp_html_result, "index.html")

    assert 'class="smf-tool-section gal-card-shell"' in html
    assert (
        'class="api-entry gal-card-entry api-profile--fastmcp-tool smf-tool-entry"'
        in html
    )
    assert 'class="api-layout"' in html
    assert 'class="api-badge-container"' in html
    assert 'class="api-facts gal-region gal-region--facts smf-body-section"' in html
    assert 'class="headerlink api-link"' in html
    assert 'class="reference internal" href="#list-sessions"' in html
    assert "Parameters" in html
    assert "readonly" in html
    assert "tool" in html
