"""Integration tests for data/attribute :value: rendering."""

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

# A module with one short and one long module-level constant. The long
# one's `repr()` will exceed the 200-char threshold and trigger truncation.
_MODULE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations


    SHORT_VALUE = 42
    \"\"\"A short module-level constant.\"\"\"


    LONG_VALUE = [
        ('one', 1),
        ('two', 2),
        ('three', 3),
        ('four', 4),
        ('five', 5),
        ('six', 6),
        ('seven', 7),
        ('eight', 8),
        ('nine', 9),
        ('ten', 10),
        ('eleven', 11),
        ('twelve', 12),
        ('thirteen', 13),
        ('fourteen', 14),
        ('fifteen', 15),
        ('sixteen', 16),
        ('seventeen', 17),
        ('eighteen', 18),
        ('nineteen', 19),
        ('twenty', 20),
    ]
    \"\"\"A long module-level constant whose repr exceeds 200 chars.\"\"\"
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
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    .. autodata:: data_defaults_demo.SHORT_VALUE

    .. autodata:: data_defaults_demo.LONG_VALUE
    """
)


@pytest.fixture(scope="module")
def data_defaults_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a Sphinx project with one short and one long data attribute."""
    cache_root = tmp_path_factory.mktemp("data-defaults-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("data_defaults_demo.py", _MODULE_SOURCE),
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
        purge_modules=("data_defaults_demo",),
    )


@pytest.mark.integration
def test_short_data_value_renders_unchanged(
    data_defaults_html_result: SharedSphinxResult,
) -> None:
    """Short data values fall through the resolver chain unchanged."""
    html = read_output(data_defaults_html_result, "index.html")

    # SHORT_VALUE = 42 should render its value as-is
    assert "SHORT_VALUE" in html
    assert ">42<" in html


@pytest.mark.integration
def test_long_data_value_is_truncated(
    data_defaults_html_result: SharedSphinxResult,
) -> None:
    """Long data values are replaced with a `<...truncated, N chars>` marker."""
    html = read_output(data_defaults_html_result, "index.html")

    assert "LONG_VALUE" in html
    # Curated text rendered (note: HTML-escaped < and >)
    assert "...truncated," in html
    assert " chars" in html
    # The original sprawling list contents must NOT appear
    assert "'fourteen'" not in html
    assert "'twenty'" not in html
