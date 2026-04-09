"""Focused end-to-end Sphinx build tests for sphinx_autodoc_pytest_fixtures."""

from __future__ import annotations

import pathlib
import textwrap

import pytest
from sphinx.util.inventory import InventoryFile

from sphinx_autodoc_pytest_fixtures import _CSS
from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)
from tests.ext.pytest_fixtures._scenario_support import (
    build_fixture_result,
    render_conf_py,
)

_HTML_SMOKE_FIXTURE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations
    import pytest

    class Server:
        \"\"\"A fake server.\"\"\"

    @pytest.fixture(scope="session")
    def my_server() -> Server:
        \"\"\"Return a fake server for testing.\"\"\"
        return Server()

    @pytest.fixture
    def TestServer() -> type[Server]:
        \"\"\"Return the Server class for direct instantiation (factory fixture).\"\"\"
        return Server
    """,
)

_HTML_SMOKE_INDEX_RST = textwrap.dedent(
    """\
    Test fixtures
    =============

    .. py:module:: fixture_mod

    .. autofixture:: fixture_mod.my_server

    .. autofixture:: fixture_mod.TestServer
    """,
)

_TEXT_SMOKE_INDEX_RST = textwrap.dedent(
    """\
    Test fixtures
    =============

    .. py:module:: fixture_mod

    .. autofixture:: fixture_mod.my_server
    """,
)

_CROSS_DOC_FIXTURE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations
    import pytest

    class Server:
        \"\"\"A fake server.\"\"\"

    @pytest.fixture(scope="session")
    def cross_server() -> Server:
        \"\"\"A session-scoped server fixture.\"\"\"
        return Server()

    @pytest.fixture
    def cross_client(cross_server: Server) -> str:
        \"\"\"A client that depends on cross_server.\"\"\"
        return f"client@{cross_server}"
    """,
)


@pytest.fixture(scope="module")
def default_html_result(spf_html_root: pathlib.Path) -> SharedSphinxResult:
    """Build the default fixture HTML scenario once per module."""
    return build_fixture_result(
        spf_html_root / "default-html",
        buildername="html",
        fixture_source=_HTML_SMOKE_FIXTURE_SOURCE,
        index_rst=_HTML_SMOKE_INDEX_RST,
        confoverrides={"pytest_fixture_lint_level": "none"},
    )


@pytest.fixture(scope="module")
def cross_document_html_result(
    spf_html_root: pathlib.Path,
) -> SharedSphinxResult:
    """Build one cross-document HTML scenario for both link-direction checks."""
    scenario_root = spf_html_root / "cross-document-html"
    conf_text = render_conf_py(scenario_root / "src").replace(
        str(scenario_root / "src"),
        SCENARIO_SRCDIR_TOKEN,
    )
    scenario = SphinxScenario(
        buildername="html",
        files=(
            ScenarioFile("fixture_mod.py", _CROSS_DOC_FIXTURE_SOURCE),
            ScenarioFile("conf.py", conf_text, substitute_srcdir=True),
            ScenarioFile(
                "index.rst",
                textwrap.dedent(
                    """\
                    Test
                    ====

                    .. toctree::

                       api
                       usage
                    """,
                ),
            ),
            ScenarioFile(
                "api.rst",
                textwrap.dedent(
                    """\
                    API
                    ===

                    .. py:module:: fixture_mod

                    .. autofixture:: fixture_mod.cross_server
                    """,
                ),
            ),
            ScenarioFile(
                "usage.rst",
                textwrap.dedent(
                    """\
                    Usage
                    =====

                    Use :fixture:`fixture_mod.cross_server` to get a server.

                    .. autofixture:: fixture_mod.cross_client
                    """,
                ),
            ),
        ),
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    return build_shared_sphinx_result(
        spf_html_root,
        scenario,
        purge_modules=("fixture_mod",),
    )


@pytest.mark.integration
def test_default_html_outputs_smoke(default_html_result) -> None:
    """The default HTML build emits badge markup, inventory, and genindex entries."""
    index_html = read_output(default_html_result, "index.html")
    genindex_html = read_output(default_html_result, "genindex.html")
    inv = InventoryFile.loads(
        (default_html_result.outdir / "objects.inv").read_bytes(),
        uri="",
    )

    assert "py:fixture" in inv.data
    assert any("my_server" in name for name in inv.data["py:fixture"])

    for css_class in (
        _CSS.BADGE_GROUP,
        _CSS.BADGE,
        _CSS.BADGE_FIXTURE,
        _CSS.BADGE_SCOPE,
        _CSS.scope("session"),
        _CSS.BADGE_KIND,
        _CSS.FACTORY,
    ):
        assert css_class in index_html
    assert 'tabindex="0"' in index_html
    assert 'class="api-layout"' in index_html
    assert 'class="api-layout-left"' in index_html
    assert 'class="api-layout-right sab-toolbar"' in index_html
    assert 'class="api-signature"' in index_html
    assert 'class="api-badge-container"' in index_html
    assert "session-scoped fixtures" in genindex_html
    assert 'href="index.html#fixture_mod.my_server"' in genindex_html


@pytest.mark.integration
def test_cross_document_fixture_reference_html_resolves(
    cross_document_html_result,
) -> None:
    """Cross-document fixture references resolve to HTML hyperlinks."""
    usage_html = read_output(cross_document_html_result, "usage.html")
    assert '<a class="reference internal"' in usage_html
    assert "cross_server" in usage_html


@pytest.mark.integration
def test_cross_document_used_by_link_html_smoke(
    cross_document_html_result,
) -> None:
    """Used-by metadata links to a consumer in another HTML document."""
    api_html = read_output(cross_document_html_result, "api.html")
    assert "Used by" in api_html
    assert 'href="usage.html#fixture_mod.cross_client"' in api_html


@pytest.mark.integration
def test_text_builder_does_not_crash(
    spf_html_root: pathlib.Path,
) -> None:
    """The text builder handles pytest fixture output without crashing."""
    result = build_fixture_result(
        spf_html_root / "text-builder",
        buildername="text",
        fixture_source=_HTML_SMOKE_FIXTURE_SOURCE,
        index_rst=_TEXT_SMOKE_INDEX_RST,
        confoverrides={"pytest_fixture_lint_level": "none"},
    )

    output_text = read_output(result, "index.txt")
    assert "my_server" in output_text
