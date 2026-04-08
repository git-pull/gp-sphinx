"""Shared synthetic Sphinx scenarios for pytest fixture extension tests."""

from __future__ import annotations

import pathlib
import textwrap

from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    ScenarioInputValue,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    derive_sphinx_scenario_cache_root,
)

FIXTURE_MOD_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations
    import typing as t
    import pytest

    class Server:
        \"\"\"A fake server.\"\"\"

    @pytest.fixture(scope="session")
    def my_server() -> Server:
        \"\"\"Return a fake server for testing.

        Use this when you need a long-lived server across the session.
        \"\"\"
        return Server()

    @pytest.fixture
    def my_client(my_server: Server) -> str:
        \"\"\"Return a fake client connected to *my_server*.\"\"\"
        return f"client@{my_server}"

    @pytest.fixture
    def home_user() -> str:
        \"\"\"Override to customise the home directory username.\"\"\"
        return "testuser"

    @pytest.fixture
    def yield_server(my_server: Server) -> t.Generator[Server, None, None]:
        \"\"\"Yield the server and tear down after the test.\"\"\"
        yield my_server

    @pytest.fixture(autouse=True)
    def auto_cleanup() -> None:
        \"\"\"Runs automatically before every test — no request needed.\"\"\"

    @pytest.fixture
    def TestServer() -> type[Server]:
        \"\"\"Return the Server class for direct instantiation (factory fixture).\"\"\"
        return Server

    @pytest.fixture(name="renamed_fixture")
    def _internal_name() -> str:
        \"\"\"Fixture with a name alias — injected as 'renamed_fixture'.\"\"\"
        return "renamed"
    """,
)

CONF_PY_TEMPLATE = """\
import sys
sys.path.insert(0, "__SCENARIO_SRCDIR__")

extensions = [
{extensions}
]

master_doc = "index"
exclude_patterns = ["_build"]
html_theme = "alabaster"
"""

INDEX_RST = textwrap.dedent(
    """\
    Test fixtures
    =============

    .. py:module:: fixture_mod

    .. autofixture:: fixture_mod.my_server

    .. autofixture:: fixture_mod.my_client

    .. autofixture:: fixture_mod.home_user
       :kind: override_hook

    .. autofixture:: fixture_mod.yield_server

    .. autofixture:: fixture_mod.auto_cleanup

    .. autofixture:: fixture_mod.TestServer

    .. autofixture:: fixture_mod._internal_name
    """,
)


def render_conf_py(
    srcdir: pathlib.Path,
    *,
    extensions: list[str] | None = None,
) -> str:
    """Render ``conf.py`` for a synthetic Sphinx project."""
    if extensions is None:
        extensions = [
            "sphinx.ext.autodoc",
            "sphinx_autodoc_pytest_fixtures",
        ]
    rendered_extensions = ",\n".join(f'    "{ext}"' for ext in extensions)
    return CONF_PY_TEMPLATE.replace(
        SCENARIO_SRCDIR_TOKEN,
        str(srcdir),
    ).format(extensions=rendered_extensions)


def build_fixture_result(
    tmp_path: pathlib.Path,
    *,
    buildername: str = "html",
    confoverrides: dict[str, ScenarioInputValue] | None = None,
    fixture_source: str | None = None,
    index_rst: str | None = None,
    index_name: str = "index.rst",
    extensions: list[str] | None = None,
) -> SharedSphinxResult:
    """Build a cached synthetic Sphinx project for fixture extension tests."""
    rendered_conf = render_conf_py(
        tmp_path / "src",
        extensions=extensions,
    ).replace(
        str(tmp_path / "src"),
        SCENARIO_SRCDIR_TOKEN,
    )
    scenario = SphinxScenario(
        buildername=buildername,
        files=(
            ScenarioFile(
                "fixture_mod.py",
                fixture_source if fixture_source is not None else FIXTURE_MOD_SOURCE,
            ),
            ScenarioFile(
                "conf.py",
                rendered_conf,
                substitute_srcdir=True,
            ),
            ScenarioFile(
                index_name,
                index_rst if index_rst is not None else INDEX_RST,
            ),
        ),
        confoverrides=confoverrides,
    )
    return build_shared_sphinx_result(
        derive_sphinx_scenario_cache_root(tmp_path),
        scenario,
        purge_modules=("fixture_mod",),
    )
