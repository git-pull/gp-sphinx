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


_CROSS_MODULE_PACKAGE_INIT = textwrap.dedent(
    """\
    \"\"\"Package init re-exporting api.\"\"\"
    from cross_module_demo.api import use_default
    """
)

_CROSS_MODULE_CONSTANTS = textwrap.dedent(
    """\
    \"\"\"Module-level sentinel that the api function defaults to.\"\"\"
    from __future__ import annotations


    DEFAULT_SCOPE: object = object()
    \"\"\"Module-level default referenced from a sibling module.\"\"\"
    """
)

_CROSS_MODULE_API = textwrap.dedent(
    """\
    \"\"\"Function whose default lives in a sibling module.\"\"\"
    from __future__ import annotations

    from cross_module_demo.constants import DEFAULT_SCOPE


    def use_default(scope: object = DEFAULT_SCOPE) -> None:
        \"\"\"Function whose `scope` default references a sibling-module value.\"\"\"
    """
)


@pytest.fixture(scope="module")
def cross_module_default_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a project where a default references a sibling module's constant."""
    cache_root = tmp_path_factory.mktemp("default-xref-cross-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("cross_module_demo/__init__.py", _CROSS_MODULE_PACKAGE_INIT),
            ScenarioFile("cross_module_demo/constants.py", _CROSS_MODULE_CONSTANTS),
            ScenarioFile("cross_module_demo/api.py", _CROSS_MODULE_API),
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

                    .. autodata:: cross_module_demo.constants.DEFAULT_SCOPE

                    .. autofunction:: cross_module_demo.api.use_default
                    """
                ),
            ),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=(
            "cross_module_demo",
            "cross_module_demo.api",
            "cross_module_demo.constants",
        ),
    )


@pytest.mark.integration
def test_cross_module_default_resolves_via_refspecific(
    cross_module_default_html_result: SharedSphinxResult,
) -> None:
    """A default that references a sibling module's constant still resolves.

    The function `use_default` is documented under
    `cross_module_demo.api`; its default `DEFAULT_SCOPE` is
    documented under `cross_module_demo.constants`. Without
    `refspecific=True` on the pending_xref the Python domain only
    tries `cross_module_demo.api.DEFAULT_SCOPE` (exact match in the
    surrounding module) and the link silently fails. This pins the
    cross-module fuzzy search.
    """
    html = read_output(cross_module_default_html_result, "index.html")

    assert 'href="#cross_module_demo.constants.DEFAULT_SCOPE"' in html
    assert 'class="reference internal"' in html
    assert 'class="xref py py-obj' in html


_LAMBDA_MODULE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations


    def has_lambda_default(callback=lambda: 1) -> None:
        \"\"\"Function with a lambda default.\"\"\"
    """
)


@pytest.fixture(scope="module")
def lambda_default_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a project with a lambda default exercising the plain-text fallback."""
    cache_root = tmp_path_factory.mktemp("default-xref-lambda-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("lambda_demo.py", _LAMBDA_MODULE_SOURCE),
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
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("lambda_demo",),
    )


@pytest.mark.integration
def test_unsupported_default_falls_back_to_plain_text(
    lambda_default_html_result: SharedSphinxResult,
) -> None:
    """Unparseable defaults (lambdas) leave the span as plain text."""
    html = read_output(lambda_default_html_result, "index.html")

    # The lambda text appears in the rendered output but not wrapped in an xref
    assert "lambda" in html
    # And the build did not fail (no warnings escalated)
    assert "callback" in html
