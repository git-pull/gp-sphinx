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
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)
from tests.ext.pytest_fixtures._scenario_support import (
    FIXTURE_MOD_SOURCE,
    build_fixture_result,
    render_conf_py,
)


@pytest.fixture(scope="module")
def fixture_integration_root(
    tmp_path_factory: pytest.TempPathFactory,
) -> pathlib.Path:
    """Return a shared cache root for fixture HTML integration scenarios."""
    return tmp_path_factory.mktemp("spf-html")


@pytest.fixture(scope="module")
def default_html_result(fixture_integration_root: pathlib.Path):
    """Build the default fixture HTML scenario once per module."""
    return build_fixture_result(
        fixture_integration_root / "default-html",
        buildername="html",
        confoverrides={"pytest_fixture_lint_level": "none"},
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
    assert "session-scoped fixtures" in genindex_html
    assert 'href="index.html#fixture_mod.my_server"' in genindex_html


@pytest.mark.integration
def test_cross_document_fixture_reference_html_resolves(
    fixture_integration_root: pathlib.Path,
) -> None:
    """Cross-document fixture references resolve to HTML hyperlinks."""
    scenario_root = fixture_integration_root / "cross-document-reference"
    conf_text = render_conf_py(scenario_root / "src").replace(
        str(scenario_root / "src"),
        SCENARIO_SRCDIR_TOKEN,
    )
    scenario = SphinxScenario(
        buildername="html",
        files=(
            ScenarioFile("fixture_mod.py", FIXTURE_MOD_SOURCE),
            ScenarioFile("conf.py", conf_text, substitute_srcdir=True),
            ScenarioFile(
                "index.rst",
                textwrap.dedent(
                    """\
                    Fixtures
                    ========

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

                    .. autofixture:: fixture_mod.my_server
                    """,
                ),
            ),
            ScenarioFile(
                "usage.rst",
                textwrap.dedent(
                    """\
                    Usage
                    =====

                    Use :fixture:`fixture_mod.my_server` to get a server.
                    """,
                ),
            ),
        ),
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    result = build_shared_sphinx_result(
        fixture_integration_root,
        scenario,
        purge_modules=("fixture_mod",),
    )

    usage_html = read_output(result, "usage.html")
    assert '<a class="reference internal"' in usage_html
    assert "my_server" in usage_html


CROSS_DOC_FIXTURE_SOURCE = textwrap.dedent(
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


@pytest.mark.integration
def test_cross_document_used_by_link_html_smoke(
    fixture_integration_root: pathlib.Path,
) -> None:
    """Used-by metadata links to a consumer in another HTML document."""
    scenario_root = fixture_integration_root / "cross-document-used-by"
    conf_text = render_conf_py(scenario_root / "src").replace(
        str(scenario_root / "src"),
        SCENARIO_SRCDIR_TOKEN,
    )
    scenario = SphinxScenario(
        buildername="html",
        files=(
            ScenarioFile("fixture_mod.py", CROSS_DOC_FIXTURE_SOURCE),
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

                    .. autofixture:: fixture_mod.cross_client
                    """,
                ),
            ),
        ),
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    result = build_shared_sphinx_result(
        fixture_integration_root,
        scenario,
        purge_modules=("fixture_mod",),
    )

    api_html = read_output(result, "api.html")
    assert "Used by" in api_html
    assert 'href="usage.html#fixture_mod.cross_client"' in api_html


@pytest.mark.integration
def test_text_builder_does_not_crash(
    fixture_integration_root: pathlib.Path,
) -> None:
    """The text builder handles pytest fixture output without crashing."""
    result = build_fixture_result(
        fixture_integration_root / "text-builder",
        buildername="text",
        confoverrides={"pytest_fixture_lint_level": "none"},
    )

    output_text = read_output(result, "index.txt")
    assert "my_server" in output_text
