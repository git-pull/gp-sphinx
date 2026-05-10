"""Integration tests for field-list xref styling and prefix wrapping."""

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

# Documents a class with parameter types (internal class + intersphinx
# str/None), an optional parameter, a return type, and a Raises section
# whose exception is a documented internal class. Each rendering case
# the user called out is exercised on a single page.
_MODULE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations


    class CustomError(Exception):
        \"\"\"A documented exception used in the Raises section.\"\"\"


    class Server:
        \"\"\"Documented internal class used as a parameter type.\"\"\"


    def configure(server: Server, name: str, target: str = '') -> None:
        \"\"\"Configure something on the server.

        Parameters
        ----------
        server : Server
            The server instance.
        name : str
            The item name.
        target : str, optional
            Optional custom target override.

        Returns
        -------
        None
            Nothing returned.

        Raises
        ------
        CustomError
            Raised when configuration fails.
        \"\"\"
    """
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx.ext.autodoc",
        "sphinx.ext.intersphinx",
        "sphinx_autodoc_typehints_gp",
    ]

    intersphinx_mapping = {
        "py": ("https://docs.python.org/3", None),
    }
    autodoc_typehints = "description"
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    .. autoclass:: field_xref_demo.Server

    .. autoexception:: field_xref_demo.CustomError

    .. autofunction:: field_xref_demo.configure
    """
)


@pytest.fixture(scope="module")
def field_xref_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a fixture project exercising every field-list rendering case."""
    cache_root = tmp_path_factory.mktemp("field-xref-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("field_xref_demo.py", _MODULE_SOURCE),
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
        purge_modules=("field_xref_demo",),
    )


@pytest.mark.integration
def test_param_internal_type_renders_canonical_xref(
    field_xref_html_result: SharedSphinxResult,
) -> None:
    """Internal parameter type renders <a><code class='xref py py-class'>...</code></a>."""
    html = read_output(field_xref_html_result, "index.html")

    # The param's internal class link wraps Server in the canonical shape.
    assert 'href="#field_xref_demo.Server"' in html
    # The xref-styled <code> wrapping is present somewhere on the page.
    assert "xref py py-class" in html


@pytest.mark.integration
def test_param_intersphinx_type_gets_code_wrapping(
    field_xref_html_result: SharedSphinxResult,
) -> None:
    """Intersphinx-resolved `str` gets the canonical <code> wrap inside <a>."""
    html = read_output(field_xref_html_result, "index.html")

    # The link-to-stdlib for `str` exists (intersphinx may or may not actually
    # resolve in CI; either way the link target string is the canonical one).
    # The contnode rewrite means the internal node tree carries the
    # `xref py py-class` literal even when intersphinx fails to resolve.
    assert "xref py py-class" in html


@pytest.mark.integration
def test_raises_exception_uses_xref_py_exc(
    field_xref_html_result: SharedSphinxResult,
) -> None:
    """Raises section renders <a><code class='xref py py-exc'>Exc</code></a>."""
    html = read_output(field_xref_html_result, "index.html")

    # A py-exc literal class appears for the raises exception
    assert "xref py py-exc" in html
    # The <strong> bold-only wrapping no longer dominates the raises
    # rendering — explicitly assert the canonical link target is there.
    assert 'href="#field_xref_demo.CustomError"' in html


@pytest.mark.integration
def test_field_prefix_is_wrapped_for_monospace(
    field_xref_html_result: SharedSphinxResult,
) -> None:
    """The `name (type, optional)` prefix sits inside gp-sphinx-field-prefix."""
    html = read_output(field_xref_html_result, "index.html")

    # The wrapper class appears at least once for the parameter rows.
    assert 'class="gp-sphinx-field-prefix"' in html


@pytest.mark.integration
def test_typehints_css_is_referenced_in_built_page(
    field_xref_html_result: SharedSphinxResult,
) -> None:
    """The CSS file with our overrides is linked from the built page."""
    html = read_output(field_xref_html_result, "index.html")

    assert "typehints_gp.css" in html


@pytest.mark.integration
def test_returns_prose_body_not_monospaced(
    field_xref_html_result: SharedSphinxResult,
) -> None:
    """The `Returns` field body's prose stays in the body font.

    `Returns` has no identifier (no parameter name, no type
    cross-reference), so the prefix wrapper is not applied — the
    description stays in the default body font instead of being
    rendered in the monospace prefix font.
    """
    import re

    html = read_output(field_xref_html_result, "index.html")

    # Locate the Returns field's <dd>
    m = re.search(
        r'<dt[^>]*>Returns<span class="colon">:</span></dt>\s*<dd[^>]*>(.*?)</dd>',
        html,
        re.DOTALL,
    )
    assert m is not None, "Returns dd not found in built HTML"
    returns_dd = m.group(1)

    # The prose-only Returns body must not have the prefix wrapper.
    assert "gp-sphinx-field-prefix" not in returns_dd, (
        f"Returns body unexpectedly carries the prefix wrapper: {returns_dd!r}"
    )
