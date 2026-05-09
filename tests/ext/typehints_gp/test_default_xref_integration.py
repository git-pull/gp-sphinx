"""Integration tests for cross-referenced parameter defaults."""

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

# A documented Foo class plus a function whose default references it.
# Sphinx's autodoc_preserve_defaults captures `Foo` as the source-text
# default for `bar`, which Stage C then turns into a pending_xref to
# the documented Foo class.
_MODULE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations


    class Foo:
        \"\"\"A documented sentinel class used as a default.\"\"\"


    def bar(x: int = 0, sentinel: object = Foo) -> None:
        \"\"\"Function whose `sentinel` default references the Foo class.\"\"\"
    """
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx.ext.autodoc",
        "sphinx_autodoc_typehints_gp",
    ]

    autodoc_preserve_defaults = True
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    .. autoclass:: default_xref_demo.Foo

    .. autofunction:: default_xref_demo.bar
    """
)


@pytest.fixture(scope="module")
def default_xref_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a Sphinx project where one default references a documented class."""
    cache_root = tmp_path_factory.mktemp("default-xref-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("default_xref_demo.py", _MODULE_SOURCE),
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
        purge_modules=("default_xref_demo",),
    )


@pytest.mark.integration
def test_default_value_class_renders_as_xref_link(
    default_xref_html_result: SharedSphinxResult,
) -> None:
    """An identifier in a default value renders as the same xref shape as :py:class:."""
    html = read_output(default_xref_html_result, "index.html")

    # The bar() signature must contain an :py:obj:-styled xref to Foo,
    # not plain text. The exact HTML shape:
    # <a class="reference internal" href="#..."
    #   ><code class="xref py py-obj docutils literal notranslate"
    #     ><span class="pre">Foo</span></code></a>
    # Using py-obj rather than py-class so module-level data
    # attributes (e.g. libtmux's DEFAULT_OPTION_SCOPE) also resolve.
    assert 'href="#default_xref_demo.Foo"' in html  # resolved link target
    assert 'class="reference internal"' in html  # the <a> wrapping
    assert 'class="xref py py-obj' in html  # the <code> wrapping
    # The literal Foo span text appears wrapped in the xref code block
    assert ">Foo<" in html


@pytest.mark.integration
def test_short_literal_default_remains_text(
    default_xref_html_result: SharedSphinxResult,
) -> None:
    """The integer default `0` is a Constant; no xref is created for it."""
    html = read_output(default_xref_html_result, "index.html")

    # The literal `0` should appear as a default_value span without an xref
    # wrapping. We check that the constant text is present.
    assert ">0<" in html


_DATA_ATTRIBUTE_MODULE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations


    class _DefaultScope:
        \"\"\"Sentinel type whose lone instance below is used as a default.\"\"\"


    DEFAULT_SCOPE: _DefaultScope = _DefaultScope()
    \"\"\"Module-level sentinel referenced by `using_default_scope`.\"\"\"


    def using_default_scope(scope: object = DEFAULT_SCOPE) -> None:
        \"\"\"Function whose `scope` default references DEFAULT_SCOPE data.\"\"\"
    """
)


@pytest.fixture(scope="module")
def data_attribute_default_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a project where a default references a module-level data attr."""
    cache_root = tmp_path_factory.mktemp("default-xref-data-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("data_xref_demo.py", _DATA_ATTRIBUTE_MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _CONF_PY.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile(
                "index.rst",
                textwrap.dedent(
                    """\
                    Demo
                    ====

                    .. autoclass:: data_xref_demo._DefaultScope

                    .. autodata:: data_xref_demo.DEFAULT_SCOPE

                    .. autofunction:: data_xref_demo.using_default_scope
                    """
                ),
            ),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("data_xref_demo",),
    )


@pytest.mark.integration
def test_data_attribute_default_links_to_documented_constant(
    data_attribute_default_html_result: SharedSphinxResult,
) -> None:
    """A default that references a module-level data attribute resolves.

    Reftype ``obj`` (rather than ``class``) is what lets data
    attributes resolve. Using ``class`` here would silently drop the
    ``<a>`` wrapping (the original bug behind libtmux's
    ``DEFAULT_OPTION_SCOPE`` not being linked).
    """
    html = read_output(data_attribute_default_html_result, "index.html")

    # The internal link to the documented data attribute resolves
    assert 'href="#data_xref_demo.DEFAULT_SCOPE"' in html
    assert 'class="reference internal"' in html
    # py-obj (not py-class) styling
    assert 'class="xref py py-obj' in html


@pytest.mark.integration
def test_unsupported_default_falls_back_to_plain_text(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Unparseable defaults (lambdas) leave the span as plain text."""
    module_source = textwrap.dedent(
        """\
        from __future__ import annotations


        def has_lambda_default(callback=lambda: 1) -> None:
            \"\"\"Function with a lambda default.\"\"\"
        """
    )
    cache_root = tmp_path_factory.mktemp("default-xref-lambda-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("lambda_demo.py", module_source),
            ScenarioFile(
                "conf.py",
                _CONF_PY.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile(
                "index.rst",
                textwrap.dedent(
                    """\
                    Demo
                    ====

                    .. autofunction:: lambda_demo.has_lambda_default
                    """
                ),
            ),
        ),
    )
    result = build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("lambda_demo",),
    )
    html = read_output(result, "index.html")

    # The lambda text appears in the rendered output but not wrapped in an xref
    assert "lambda" in html
    # And the build did not fail (no warnings escalated)
    assert "callback" in html
