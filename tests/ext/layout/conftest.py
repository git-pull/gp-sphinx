"""Shared fixtures for layout integration and snapshot tests."""

from __future__ import annotations

import pathlib
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


    class LayoutDemo:
        \"\"\"A class demonstrating all layout regions.

        Parameters
        ----------
        host : str
            Server hostname.
        port : int
            Server port number.
        username : str
            Authentication username.
        password : str
            Authentication password.
        database : str
            Database name.
        timeout : float
            Connection timeout in seconds.
        retries : int
            Number of connection retries.
        ssl : bool
            Enable SSL/TLS.
        pool_size : int
            Connection pool size.
        pool_timeout : float
            Pool checkout timeout.
        echo : bool
            Log all SQL statements.
        encoding : str
            Character encoding.
        isolation_level : str
            Transaction isolation level.
        \"\"\"

        def __init__(
            self,
            host: str,
            port: int = 5432,
            *,
            username: str = "admin",
            password: str = "",
            database: str = "default",
            timeout: float = 30.0,
            retries: int = 3,
            ssl: bool = True,
            pool_size: int = 5,
            pool_timeout: float = 10.0,
            echo: bool = False,
            encoding: str = "utf-8",
            isolation_level: str = "READ COMMITTED",
        ) -> None:
            self.host = host
            self.port = port

        def connect(self) -> bool:
            \"\"\"Open a connection to the server.\"\"\"
            return True
    """
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import pathlib
    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx.ext.autodoc",
        "sphinx.ext.viewcode",
        "sphinx_autodoc_typehints_gp",
        "sphinx_autodoc_api_style",
        "sphinx_ux_autodoc_layout",
    ]

    api_layout_enabled = True
    api_fold_parameters = True
    api_collapsed_threshold = 10
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Layout Demo
    ===========

    .. autoclass:: api_demo_layout.LayoutDemo
       :members:
       :special-members: __init__
    """
)


@pytest.fixture(scope="session")
def layout_cache_root(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """Return a shared cache root for layout HTML scenarios."""
    return tmp_path_factory.mktemp("layout-html")


def _build_layout_demo_result(
    cache_root: pathlib.Path,
    *,
    extra_conf: str = "",
) -> SharedSphinxResult:
    conf_text = _CONF_PY
    if extra_conf:
        conf_text = f"{conf_text.rstrip()}\n{extra_conf}\n"
    scenario = SphinxScenario(
        files=(
            ScenarioFile("api_demo_layout.py", _MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                conf_text.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _INDEX_RST),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("api_demo_layout",),
    )


def _build_layout_demo(
    cache_root: pathlib.Path,
    *,
    extra_conf: str = "",
) -> str:
    return read_output(
        _build_layout_demo_result(cache_root, extra_conf=extra_conf),
        "index.html",
    )


@pytest.fixture(scope="session")
def layout_default_html(layout_cache_root: pathlib.Path) -> str:
    """Build the default layout demo HTML once per test session."""
    return _build_layout_demo(layout_cache_root / "default")
