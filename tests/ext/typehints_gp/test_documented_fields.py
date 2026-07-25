"""Tests for sphinx_autodoc_typehints_gp._documented_fields."""

from __future__ import annotations

import dataclasses
import textwrap
import typing as t

import pytest
from docutils import nodes
from sphinx import addnodes

from sphinx_autodoc_typehints_gp._documented_fields import (
    _is_declared_field,
    _numpy_attribute_names,
)
from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    get_doctree,
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
# _is_declared_field
# ---------------------------------------------------------------------------


class _Point(t.NamedTuple):
    """A point in two dimensions."""

    x: int


@dataclasses.dataclass
class _Rule:
    """A rule carrying fields with and without defaults."""

    label: str
    weight: int = 0
    registry: t.ClassVar[dict[str, str]] = {}  # noqa: RUF012

    @property
    def slug(self) -> str:
        """Return the label lowercased."""
        return self.label.lower()

    def matches(self, other: str) -> bool:
        """Return whether ``other`` equals the label."""
        return self.label == other


class _BaseOptions(t.TypedDict):
    """Options every caller may pass."""

    name: str


class _Options(_BaseOptions):
    """Options with one key of its own."""

    retries: int


class _DeclaredFieldFixture(t.NamedTuple):
    """Test case for _is_declared_field().

    Attributes
    ----------
    test_id : str
        Short identifier used as the pytest parameter id.
    klass : type
        Class whose member is being classified.
    name : str
        Member name handed to the classifier.
    expected : bool
        Whether the member is expected to count as a declared field.
    """

    test_id: str
    klass: type
    name: str
    expected: bool


_DECLARED_FIELD_FIXTURES: list[_DeclaredFieldFixture] = [
    _DeclaredFieldFixture(
        test_id="namedtuple-field",
        klass=_Point,
        name="x",
        expected=True,
    ),
    _DeclaredFieldFixture(
        test_id="namedtuple-method",
        klass=_Point,
        name="_replace",
        expected=False,
    ),
    _DeclaredFieldFixture(
        test_id="dataclass-field-without-default",
        klass=_Rule,
        name="label",
        expected=True,
    ),
    _DeclaredFieldFixture(
        test_id="dataclass-field-with-default",
        klass=_Rule,
        name="weight",
        expected=True,
    ),
    _DeclaredFieldFixture(
        test_id="dataclass-classvar",
        klass=_Rule,
        name="registry",
        expected=False,
    ),
    _DeclaredFieldFixture(
        test_id="dataclass-property",
        klass=_Rule,
        name="slug",
        expected=False,
    ),
    _DeclaredFieldFixture(
        test_id="dataclass-method",
        klass=_Rule,
        name="matches",
        expected=False,
    ),
    _DeclaredFieldFixture(
        test_id="typeddict-own-key",
        klass=_Options,
        name="retries",
        expected=True,
    ),
    _DeclaredFieldFixture(
        test_id="typeddict-inherited-key",
        klass=_Options,
        name="name",
        expected=True,
    ),
    _DeclaredFieldFixture(
        test_id="undeclared-name",
        klass=_Options,
        name="missing",
        expected=False,
    ),
]


@pytest.mark.parametrize(
    list(_DeclaredFieldFixture._fields),
    _DECLARED_FIELD_FIXTURES,
    ids=[fixture.test_id for fixture in _DECLARED_FIELD_FIXTURES],
)
def test_is_declared_field(
    test_id: str,
    klass: type,
    name: str,
    expected: bool,
) -> None:
    """Declared fields count; methods, properties, and ClassVars do not."""
    assert _is_declared_field(klass, name) is expected


# ---------------------------------------------------------------------------
# autodoc-skip-member integration
# ---------------------------------------------------------------------------


class _MemberDescription(t.NamedTuple):
    """One member description a built document renders.

    Attributes
    ----------
    objtype : str
        Python domain object type the description carries.
    fullname : str
        Dotted name relative to its module, e.g. ``Point.x``.
    signature : str
        Rendered signature text.
    """

    objtype: str
    fullname: str
    signature: str


def _described_members(doctree: nodes.document) -> list[_MemberDescription]:
    """Return every member description in ``doctree``, in rendered order."""
    return [
        _MemberDescription(
            objtype=signature.parent.get("objtype", ""),
            fullname=signature.get("fullname", ""),
            signature=signature.astext(),
        )
        for signature in doctree.findall(addnodes.desc_signature)
    ]


def _attribute_names(result: SharedSphinxResult) -> list[str]:
    """Return the dotted name of every attribute description on ``index``."""
    return [
        member.fullname
        for member in _described_members(get_doctree(result, "index"))
        if member.objtype == "attribute"
    ]


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


def _conf_file() -> ScenarioFile:
    """Return a ``conf.py`` putting the scenario srcdir on ``sys.path``."""
    return ScenarioFile(
        "conf.py",
        _CONF_PY.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
        substitute_srcdir=True,
    )


_FIELDS_MODULE_SOURCE = textwrap.dedent(
    '''\
    from __future__ import annotations

    import dataclasses
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


    @dataclasses.dataclass
    class Rule:
        """A matching rule.

        Attributes
        ----------
        label : str
            Human readable name.
        weight : int
            Higher weights win ties.
        """

        label: str
        weight: int = 0


    class BaseOptions(t.TypedDict):
        """Options every caller may pass.

        Attributes
        ----------
        name : str
            Identifier for the run.
        """

        name: str


    class Options(BaseOptions):
        """Options a run accepts.

        Attributes
        ----------
        name : str
            Identifier for the run.
        retries : int
            Attempts before giving up.
        """

        retries: int
    '''
)

_FIELDS_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    .. autoclass:: documented_fields_demo.Point

    .. autoclass:: documented_fields_demo.Span

    .. autoclass:: documented_fields_demo.Rule

    .. autoclass:: documented_fields_demo.BaseOptions

    .. autoclass:: documented_fields_demo.Options
    """
)


@pytest.fixture(scope="module")
def documented_fields_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a project of NamedTuple, dataclass, and TypedDict field owners."""
    cache_root = tmp_path_factory.mktemp("documented-fields-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("documented_fields_demo.py", _FIELDS_MODULE_SOURCE),
            _conf_file(),
            ScenarioFile("index.rst", _FIELDS_INDEX_RST),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("documented_fields_demo",),
    )


@pytest.mark.integration
def test_documented_field_has_no_duplicate_warning(
    documented_fields_html_result: SharedSphinxResult,
) -> None:
    """A documented field is described once, whatever shape declared it."""
    assert "duplicate object description" not in (
        documented_fields_html_result.warnings
    )


@pytest.mark.integration
def test_documented_namedtuple_field_keeps_its_description(
    documented_fields_html_result: SharedSphinxResult,
) -> None:
    """The surviving description is the one the Attributes section wrote."""
    html = read_output(documented_fields_html_result, "index.html")

    assert html.count('id="documented_fields_demo.Point.x"') == 1
    assert "Horizontal offset." in html
    assert "Alias for field number 0" not in html


@pytest.mark.integration
def test_documented_dataclass_fields_keep_their_descriptions(
    documented_fields_html_result: SharedSphinxResult,
) -> None:
    """A dataclass field is described once, with or without a default."""
    attributes = _attribute_names(documented_fields_html_result)

    assert attributes.count("Rule.label") == 1
    assert attributes.count("Rule.weight") == 1
    assert "Higher weights win ties." in read_output(
        documented_fields_html_result, "index.html"
    )


@pytest.mark.integration
def test_documented_typeddict_keys_keep_their_descriptions(
    documented_fields_html_result: SharedSphinxResult,
) -> None:
    """A TypedDict key is described once, including one a base declares."""
    attributes = _attribute_names(documented_fields_html_result)

    assert attributes.count("Options.name") == 1
    assert attributes.count("Options.retries") == 1
    assert "Attempts before giving up." in read_output(
        documented_fields_html_result, "index.html"
    )


@pytest.mark.integration
def test_undocumented_field_still_renders(
    documented_fields_html_result: SharedSphinxResult,
) -> None:
    """A field the Attributes section omits is left to autodoc."""
    html = read_output(documented_fields_html_result, "index.html")

    assert html.count('id="documented_fields_demo.Span.stop"') == 1
    assert "Alias for field number 1" in html


# ---------------------------------------------------------------------------
# members named in an Attributes section that are not fields
# ---------------------------------------------------------------------------

_NON_FIELD_MODULE_SOURCE = textwrap.dedent(
    '''\
    from __future__ import annotations

    import typing as t


    class Facade:
        """A facade over registered backends.

        Attributes
        ----------
        registry : dict[str, str]
            Backends registered so far.
        summary : str
            One-line description of the registry.
        """

        registry: t.ClassVar[dict[str, str]] = {}

        @property
        def summary(self) -> str:
            """Return how many backends are registered."""
            return f"{len(self.registry)} backends"
    '''
)

_NON_FIELD_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    .. autoclass:: non_field_members_demo.Facade
    """
)


@pytest.fixture(scope="module")
def non_field_members_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a project whose Attributes section names a ClassVar and a property."""
    cache_root = tmp_path_factory.mktemp("non-field-members-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("non_field_members_demo.py", _NON_FIELD_MODULE_SOURCE),
            _conf_file(),
            ScenarioFile("index.rst", _NON_FIELD_INDEX_RST),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("non_field_members_demo",),
    )


@pytest.mark.integration
def test_property_named_in_attributes_still_renders(
    non_field_members_html_result: SharedSphinxResult,
) -> None:
    """A property stays autodoc's to render even when Attributes names it."""
    members = _described_members(get_doctree(non_field_members_html_result, "index"))

    assert [member.fullname for member in members if member.objtype == "property"] == [
        "Facade.summary"
    ]
    assert "Return how many backends are registered." in read_output(
        non_field_members_html_result, "index.html"
    )


@pytest.mark.integration
def test_classvar_named_in_attributes_still_renders(
    non_field_members_html_result: SharedSphinxResult,
) -> None:
    """A ClassVar keeps the value only autodoc renders for it."""
    members = _described_members(get_doctree(non_field_members_html_result, "index"))

    assert [
        member.signature
        for member in members
        if member.fullname == "Facade.registry" and "{}" in member.signature
    ] == ["registry: ClassVar[dict[str, str]] = {}"]
