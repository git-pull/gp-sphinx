"""Integration tests for sphinx_autodoc_docutils layout consumption."""

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

    from docutils import nodes
    from docutils.parsers.rst import Directive, directives
    from docutils.readers import Reader
    from docutils.transforms import Transform


    class DemoDirective(Directive):
        required_arguments = 1
        optional_arguments = 0
        has_content = True
        option_spec = {"class": directives.class_option}

        def run(self):
            paragraph = nodes.paragraph("", "Directive body.")
            return [paragraph]


    def demo_role(
        name,
        rawtext,
        text,
        lineno,
        inliner,
        options=None,
        content=None,
    ):
        return [nodes.literal(text, text)], []


    demo_role.options = {"class": directives.class_option}
    demo_role.content = True


    class DemoTransform(Transform):
        \"\"\"Reorder demo paragraphs after parsing.\"\"\"

        default_priority = 765

        def apply(self):
            pass


    class DemoReader(Reader):
        \"\"\"Read demo article sources.\"\"\"

        supported = ("demo-article",)
        config_section = "demo reader"

        def get_transforms(self):
            return [*super().get_transforms(), DemoTransform]


    def setup(app):
        app.add_transform(DemoTransform)
    """
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx_autodoc_docutils",
    ]
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Demo docutils
    =============

    .. autodirective:: demo_docutils_objects.DemoDirective

    .. autorole:: demo_docutils_objects.demo_role

    .. autotransform:: demo_docutils_objects.DemoTransform

    .. autotransforms:: demo_docutils_objects
       :no-index:

    .. autoreader:: demo_docutils_objects.DemoReader
    """
)


@pytest.fixture(scope="module")
def autodoc_docutils_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    cache_root = tmp_path_factory.mktemp("autodoc-docutils-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("demo_docutils_objects.py", _MODULE_SOURCE),
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
        purge_modules=("demo_docutils_objects",),
    )


@pytest.mark.integration
def test_autodoc_docutils_entries_use_shared_layout(
    autodoc_docutils_html_result: SharedSphinxResult,
) -> None:
    html = read_output(autodoc_docutils_html_result, "index.html")

    assert "gp-sphinx-api-profile--rst-directive" in html
    assert "gp-sphinx-api-profile--rst-directive-option" in html
    assert "gp-sphinx-api-profile--rst-role" in html
    assert (
        'class="gp-sphinx-api-facts gp-sphinx-api-region gp-sphinx-api-region--facts"'
        in html
    )
    assert (
        'class="gp-sphinx-api-options gp-sphinx-api-region gp-sphinx-api-region--options"'
        in html
    )
    assert 'class="gp-sphinx-api-badge-container"' in html
    assert ">directive<" in html
    assert ">option<" in html
    assert ">role<" in html
    assert "Python path" in html


@pytest.mark.integration
def test_autodoc_docutils_transform_entries(
    autodoc_docutils_html_result: SharedSphinxResult,
) -> None:
    """autotransform entries render with profile, badges, and facts."""
    html = read_output(autodoc_docutils_html_result, "index.html")

    assert "gp-sphinx-api-profile--docutils-transform" in html
    assert ">transform<" in html
    assert "gp-sphinx-badge--mod-priority" in html
    assert ">765<" in html
    assert "Default priority" in html
    assert "app.add_transform()" in html


@pytest.mark.integration
def test_autodoc_docutils_reader_entries(
    autodoc_docutils_html_result: SharedSphinxResult,
) -> None:
    """autoreader entries render with profile, badge, and facts."""
    html = read_output(autodoc_docutils_html_result, "index.html")

    assert "gp-sphinx-api-profile--docutils-reader" in html
    assert ">reader<" in html
    assert "Supported formats" in html
    assert "demo-article" in html
    assert "DemoTransform" in html
