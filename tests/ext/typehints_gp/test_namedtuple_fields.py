"""Tests for sphinx_autodoc_typehints_gp._namedtuple_fields."""

from __future__ import annotations

import textwrap
import typing as t

import pytest

from sphinx_autodoc_typehints_gp._namedtuple_fields import _numpy_attribute_names
from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

# ---------------------------------------------------------------------------
# _numpy_attribute_names
# ---------------------------------------------------------------------------


class _AttributeNamesFixture(t.NamedTuple):
    """Test case for _numpy_attribute_names().

    Attributes
    ----------
    test_id : str
        Short identifier used as the pytest parameter id.
    doc : str | None
        Docstring handed to the parser.
    expected : frozenset[str]
        Names the ``Attributes`` section is expected to describe.
    """

    test_id: str
    doc: str | None
    expected: frozenset[str]


_ATTRIBUTE_NAMES_FIXTURES: list[_AttributeNamesFixture] = [
    _AttributeNamesFixture(
        test_id="none",
        doc=None,
        expected=frozenset(),
    ),
    _AttributeNamesFixture(
        test_id="summary-only",
        doc="A point.",
        expected=frozenset(),
    ),
    _AttributeNamesFixture(
        test_id="indented-section",
        doc="""A point.

        Attributes
        ----------
        x : int
            Horizontal offset.
        y : int
            Vertical offset.
        """,
        expected=frozenset({"x", "y"}),
    ),
    _AttributeNamesFixture(
        test_id="other-sections-ignored",
        doc="""Build a point.

        Parameters
        ----------
        x : int
            Horizontal offset.

        Returns
        -------
        Point
            The point.
        """,
        expected=frozenset(),
    ),
    _AttributeNamesFixture(
        test_id="attributes-among-other-sections",
        doc="""A point.

        Attributes
        ----------
        x : int
            Horizontal offset.

        Examples
        --------
        >>> Point(1, 2).x
        1
        """,
        expected=frozenset({"x"}),
    ),
]


@pytest.mark.parametrize(
    list(_AttributeNamesFixture._fields),
    _ATTRIBUTE_NAMES_FIXTURES,
    ids=[fixture.test_id for fixture in _ATTRIBUTE_NAMES_FIXTURES],
)
def test_numpy_attribute_names(
    test_id: str,
    doc: str | None,
    expected: frozenset[str],
) -> None:
    """Only an Attributes section contributes documented member names."""
    assert _numpy_attribute_names(doc) == expected


# ---------------------------------------------------------------------------
# autodoc-skip-member integration
# ---------------------------------------------------------------------------

_MODULE_SOURCE = textwrap.dedent(
    '''\
    from __future__ import annotations

    import typing as t


    class Point(t.NamedTuple):
        """A point in two dimensions.

        Attributes
        ----------
        x : int
            Horizontal offset.
        y : int
            Vertical offset.
        """

        x: int
        y: int


    class Span(t.NamedTuple):
        """A half-open interval.

        Attributes
        ----------
        start : int
            Inclusive lower bound.
        """

        start: int
        stop: int
    '''
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
    autodoc_default_options = {"members": True, "undoc-members": True}
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    .. autoclass:: namedtuple_fields_demo.Point

    .. autoclass:: namedtuple_fields_demo.Span
    """
)


@pytest.fixture(scope="module")
def namedtuple_fields_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a project with fully and partially documented NamedTuples."""
    cache_root = tmp_path_factory.mktemp("namedtuple-fields-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("namedtuple_fields_demo.py", _MODULE_SOURCE),
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
        purge_modules=("namedtuple_fields_demo",),
    )


@pytest.mark.integration
def test_documented_field_has_no_duplicate_warning(
    namedtuple_fields_html_result: SharedSphinxResult,
) -> None:
    """A documented NamedTuple field is described once, not twice."""
    assert "duplicate object description" not in (
        namedtuple_fields_html_result.warnings
    )


@pytest.mark.integration
def test_documented_field_keeps_its_description(
    namedtuple_fields_html_result: SharedSphinxResult,
) -> None:
    """The surviving description is the one the Attributes section wrote."""
    html = read_output(namedtuple_fields_html_result, "index.html")

    assert html.count('id="namedtuple_fields_demo.Point.x"') == 1
    assert "Horizontal offset." in html
    assert "Alias for field number 0" not in html


@pytest.mark.integration
def test_undocumented_field_still_renders(
    namedtuple_fields_html_result: SharedSphinxResult,
) -> None:
    """A field the Attributes section omits is left to autodoc."""
    html = read_output(namedtuple_fields_html_result, "index.html")

    assert html.count('id="namedtuple_fields_demo.Span.stop"') == 1
    assert "Alias for field number 1" in html
