"""Integration tests for sphinx_autodoc_sphinx layout consumption."""

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


    def setup(app):
        app.add_config_value(
            "demo_option",
            True,
            "env",
            types=(bool,),
            description="Enable the demo option.",
        )
        app.add_config_value(
            "demo_palette",
            {
                "accent": "teal",
                "surface": "paper",
                "ink": "charcoal",
                "callouts": ("tip", "warning", "danger"),
            },
            "html",
            types=(dict,),
            description="Color tokens for the demo extension.",
        )
    """
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx_autodoc_sphinx",
    ]
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Demo config
    ===========

    .. autoconfigvalues:: demo_sphinx_ext
    """
)


@pytest.fixture(scope="module")
def autodoc_sphinx_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    cache_root = tmp_path_factory.mktemp("autodoc-sphinx-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("demo_sphinx_ext.py", _MODULE_SOURCE),
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
        purge_modules=("demo_sphinx_ext",),
    )


@pytest.mark.integration
def test_autodoc_sphinx_confvals_use_shared_layout(
    autodoc_sphinx_html_result: SharedSphinxResult,
) -> None:
    html = read_output(autodoc_sphinx_html_result, "index.html")

    assert 'class="std confval api-container api-profile--confval"' in html
    assert 'class="api-layout"' in html
    assert 'class="api-badge-container"' in html
    assert 'class="api-facts gal-region gal-region--facts"' in html
    assert "config" in html
    assert ">env<" in html
    assert ">html<" in html
    assert "Registered by" in html
    assert "highlight-python" in html
    assert "Rebuild:" not in html
