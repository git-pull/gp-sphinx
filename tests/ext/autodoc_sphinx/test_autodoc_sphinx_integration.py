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

    from sphinx.builders import Builder
    from sphinx.domains import Domain, ObjType
    from sphinx.roles import XRefRole


    class DemoZipBuilder(Builder):
        \"\"\"Bundle rendered pages into a zip archive.\"\"\"

        name = "demo-zip"
        format = "zip"
        epilog = "The zip is in %(outdir)s."
        supported_image_types = ["image/png"]

        def get_outdated_docs(self):
            return []

        def get_target_uri(self, docname, typ=None):
            return docname

        def prepare_writing(self, docnames):
            pass

        def write_doc(self, docname, doctree):
            pass


    class DemoRecipeDomain(Domain):
        \"\"\"Describe demo recipes.\"\"\"

        name = "demorecipe"
        label = "Demo recipes"
        object_types = {"recipe": ObjType("recipe", "recipe")}
        roles = {"recipe": XRefRole()}


    def setup(app):
        app.add_domain(DemoRecipeDomain)
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
        app.add_builder(DemoZipBuilder)
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

    .. autobuilder:: demo_sphinx_ext.DemoZipBuilder

    .. autodomain:: demo_sphinx_ext.DemoRecipeDomain
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

    assert (
        'class="std confval gp-sphinx-api-container gp-sphinx-api-profile--confval"'
        in html
    )
    assert "gp-sphinx-api-layout--desktop" in html
    assert "gp-sphinx-api-layout--mobile" in html
    assert 'class="gp-sphinx-api-badge-container"' in html
    assert (
        'class="gp-sphinx-api-facts gp-sphinx-api-region gp-sphinx-api-region--facts"'
        in html
    )
    assert "config" in html
    assert ">env<" in html
    assert ">html<" in html
    assert "Registered by" in html
    assert "highlight-python" in html
    assert "Rebuild:" not in html


@pytest.mark.integration
def test_autodoc_sphinx_builder_entries(
    autodoc_sphinx_html_result: SharedSphinxResult,
) -> None:
    """autobuilder entries render with profile, badges, and facts."""
    html = read_output(autodoc_sphinx_html_result, "index.html")

    assert "gp-sphinx-api-profile--sphinxext-builder" in html
    assert ">builder<" in html
    assert "gp-sphinx-badge--mod-format" in html
    assert ">zip<" in html
    assert "Builder name" in html
    assert "demo-zip" in html
    assert "image/png" in html
    assert "Parallel-safe" in html


@pytest.mark.integration
def test_autodoc_sphinx_domain_entries(
    autodoc_sphinx_html_result: SharedSphinxResult,
) -> None:
    """autodomain entries render with profile, badges, and facts."""
    html = read_output(autodoc_sphinx_html_result, "index.html")

    assert "gp-sphinx-api-profile--sphinxext-domain" in html
    assert ">domain<" in html
    assert "gp-sphinx-badge--mod-domain-name" in html
    assert ">demorecipe<" in html
    assert "Object types" in html
    assert ">recipe<" in html
    # Literal body text splits into per-word <span class="pre"> chunks.
    assert ">recipes<" in html


@pytest.mark.integration
def test_config_type_fact_links_with_env(
    autodoc_sphinx_html_result: SharedSphinxResult,
) -> None:
    """With a live environment the Type fact carries py-domain xrefs."""
    from sphinx import addnodes

    from sphinx_autodoc_sphinx._directives import (
        SphinxConfigValue,
        _config_fact_rows,
    )

    value = SphinxConfigValue("demo_ext", "demo_option", True, "html", (bool,))
    rows = _config_fact_rows(value, env=autodoc_sphinx_html_result.app.env)
    type_row = next(row for row in rows if row.label == "Type")
    xref = next(iter(type_row.body.findall(addnodes.pending_xref)))
    assert xref["reftarget"] == "bool"
    assert type_row.body.astext() == "bool"
