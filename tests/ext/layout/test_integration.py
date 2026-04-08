"""Integration tests for sphinx_autodoc_layout HTML output."""

from __future__ import annotations

import pathlib
import re
import textwrap

import pytest

from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SphinxScenario,
    build_shared_sphinx_result,
    derive_sphinx_scenario_cache_root,
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
        "sphinx.ext.napoleon",
        "sphinx.ext.viewcode",
        "sphinx_autodoc_api_style",
        "sphinx_autodoc_layout",
    ]

    gal_enabled = True
    gal_fold_parameters = True
    gal_collapsed_threshold = 10
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Layout Demo
    ===========

    .. autoclass:: gal_demo_api.LayoutDemo
       :members:
       :special-members: __init__
    """
)


def _extract_init_header(html: str) -> str:
    """Return the full ``LayoutDemo.__init__`` header fragment."""
    init_match = re.search(
        r'(<dt (?=[^>]*class="[^"]*api-header[^"]*")'
        r'(?=[^>]*id="gal_demo_api\.LayoutDemo\.__init__")[^>]*>.*?</dt>)',
        html,
        re.DOTALL,
    )
    assert init_match is not None
    return init_match.group(1).strip()


def _build_layout_demo(
    tmp_path: pathlib.Path,
    *,
    extra_conf: str = "",
) -> str:
    conf_text = _CONF_PY
    if extra_conf:
        conf_text = f"{conf_text.rstrip()}\n{extra_conf}\n"
    scenario = SphinxScenario(
        files=(
            ScenarioFile("gal_demo_api.py", _MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                conf_text.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _INDEX_RST),
        ),
    )
    result = build_shared_sphinx_result(
        derive_sphinx_scenario_cache_root(tmp_path),
        scenario,
        purge_modules=("gal_demo_api",),
    )
    return (result.outdir / "index.html").read_text(encoding="utf-8")


@pytest.mark.integration
def test_layout_demo_renders_api_component_contract(tmp_path: pathlib.Path) -> None:
    html = _build_layout_demo(tmp_path)

    assert re.search(r'<dl class="[^"]*api-container[^"]*">', html)
    assert re.search(r'<dd class="[^"]*api-content[^"]*">', html)
    assert 'class="api-description gal-region gal-region--narrative"' in html
    assert 'class="api-parameters gal-region gal-region--fields"' in html
    assert 'class="api-footer gal-region gal-region--members"' in html
    assert '<details class="gal-fold gal-fold--parameters">' in html
    assert 'class="gal-sig-fold"' not in html

    init_html = _extract_init_header(html)

    assert 'data-signature-expanded="false"' in init_html
    assert '<div class="api-layout" data-signature-expanded=' not in init_html
    assert re.search(
        r'<dt [^>]*class="[^"]*api-header[^"]*"[^>]*data-signature-expanded="false"',
        init_html,
    )
    assert 'class="api-layout"' in init_html
    assert 'class="api-layout-left"' in init_html
    assert 'class="api-layout-right gas-toolbar"' in init_html
    assert 'class="api-signature"' in init_html
    assert 'class="headerlink api-link"' in init_html
    assert 'class="api-badge-container"' in init_html
    assert 'class="api-source-link"' in init_html
    assert 'class="api-signature-expanded gal-sig-expanded"' in init_html
    assert (
        'aria-controls="gal_demo_api.LayoutDemo.__init__--signature-expanded"'
        in init_html
    )
    assert 'id="gal_demo_api.LayoutDemo.__init__--signature-expanded"' in init_html
    assert "<dl>" in init_html
    assert '<span class="sig-paren">(</span>' in init_html
    assert '<span class="sig-paren">)</span>' in init_html
    assert 'class="gal-sig-collapse"' in init_html
    assert "[collapse]" in init_html
    assert re.search(
        r'<span class="sig-paren">\)</span>\s*<button[^>]*class="[^"]*gal-sig-collapse[^"]*"',
        init_html,
    )
    assert "host" in init_html
    assert "port" in init_html
    assert "str" in init_html
    assert "int" in init_html
    assert "[source]" in init_html
    assert "api-signature-panel" not in init_html


@pytest.mark.integration
def test_layout_demo_members_stay_in_api_footer(tmp_path: pathlib.Path) -> None:
    html = _build_layout_demo(tmp_path)

    footer_start = html.find('class="api-footer gal-region gal-region--members"')
    assert footer_start != -1
    footer_html = html[footer_start:]

    assert "gal_demo_api.LayoutDemo.__init__" in footer_html
    assert "gal_demo_api.LayoutDemo.connect" in footer_html


@pytest.mark.integration
def test_layout_demo_can_hide_folded_signature_annotations(
    tmp_path: pathlib.Path,
) -> None:
    html = _build_layout_demo(
        tmp_path,
        extra_conf="gal_signature_show_annotations = False",
    )

    init_html = _extract_init_header(html)

    assert 'class="api-signature-expanded gal-sig-expanded"' in init_html
    assert "host" in init_html
    assert "port" in init_html
    assert "port</span></span><span" in init_html
    assert "5432" in init_html
    assert '<span class="pre">str</span>' not in init_html
    assert '<span class="pre">int</span>' not in init_html
