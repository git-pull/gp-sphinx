"""Tests for sphinx_autodoc_typehints_gp._documented_fields."""

from __future__ import annotations

import dataclasses
import sys
import textwrap
import typing as t

import pytest
from docutils import nodes
from sphinx import addnodes

from sphinx_autodoc_typehints_gp._documented_fields import (
    _attribute_directive_names,
    _is_declared_field,
    _own_annotations,
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
# _attribute_directive_names
# ---------------------------------------------------------------------------


class _AttributeDirectiveNamesFixture(t.NamedTuple):
    """Test case for _attribute_directive_names().

    Attributes
    ----------
    test_id : str
        Short identifier used as the pytest parameter id.
    lines : list[str]
        Processed docstring lines handed to the collector.
    expected : frozenset[str]
        Names the directives are expected to describe.
    """

    test_id: str
    lines: list[str]
    expected: frozenset[str]


_ATTRIBUTE_DIRECTIVE_NAMES_FIXTURES: list[_AttributeDirectiveNamesFixture] = [
    _AttributeDirectiveNamesFixture(
        test_id="empty",
        lines=[],
        expected=frozenset(),
    ),
    _AttributeDirectiveNamesFixture(
        test_id="summary-only",
        lines=["A point."],
        expected=frozenset(),
    ),
    _AttributeDirectiveNamesFixture(
        test_id="attribute-directives",
        lines=[
            ".. attribute:: x",
            "",
            "   Horizontal offset.",
            ".. attribute:: y",
        ],
        expected=frozenset({"x", "y"}),
    ),
    _AttributeDirectiveNamesFixture(
        test_id="other-directive",
        lines=[".. method:: build()"],
        expected=frozenset(),
    ),
]


@pytest.mark.parametrize(
    list(_AttributeDirectiveNamesFixture._fields),
    _ATTRIBUTE_DIRECTIVE_NAMES_FIXTURES,
    ids=[fixture.test_id for fixture in _ATTRIBUTE_DIRECTIVE_NAMES_FIXTURES],
)
def test_attribute_directive_names(
    test_id: str,
    lines: list[str],
    expected: frozenset[str],
) -> None:
    """Only emitted attribute directives contribute documented names."""
    assert _attribute_directive_names(lines) == expected


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


@dataclasses.dataclass(slots=True)
class _Gauge:
    """A rule whose fields live in slots."""

    reading: int
    scale: int = 1

    @property
    def scaled(self) -> int:
        """Return the reading multiplied by the scale."""
        return self.reading * self.scale


class _IntegerField:
    """Store an integer while exposing a class-level default."""

    def __get__(self, obj: object | None, owner: type | None = None) -> int:
        """Return the stored value or the class-level default."""
        if obj is None:
            return 0
        return t.cast("int", vars(obj).get("_reading", 0))

    def __set__(self, obj: object, value: int) -> None:
        """Store ``value`` on ``obj``."""
        vars(obj)["_reading"] = value


@dataclasses.dataclass
class _DescriptorGauge:
    """A dataclass whose field is backed by a descriptor."""

    reading: int = _IntegerField()  # type: ignore[assignment]


class _AnnotatedMethod:
    """A class retaining an annotation for a same-named method."""

    matches: t.Callable[[str], bool]

    def matches(self, other: str) -> bool:  # type: ignore[no-redef]
        """Return whether ``other`` is non-empty."""
        return bool(other)


class _QuotedClassVar:
    """A class with an explicitly quoted postponed annotation."""

    registry: "t.ClassVar[dict[str, str]]" = {}


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
        test_id="slotted-dataclass-field",
        klass=_Gauge,
        name="reading",
        expected=True,
    ),
    _DeclaredFieldFixture(
        test_id="slotted-dataclass-property",
        klass=_Gauge,
        name="scaled",
        expected=False,
    ),
    _DeclaredFieldFixture(
        test_id="descriptor-dataclass-field",
        klass=_DescriptorGauge,
        name="reading",
        expected=True,
    ),
    _DeclaredFieldFixture(
        test_id="annotated-method",
        klass=_AnnotatedMethod,
        name="matches",
        expected=False,
    ),
    _DeclaredFieldFixture(
        test_id="quoted-classvar",
        klass=_QuotedClassVar,
        name="registry",
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


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="deferred annotations are the Python 3.14 default",
)
def test_own_annotations_does_not_evaluate_deferred_annotation() -> None:
    """Reading field names does not execute a deferred annotation."""
    namespace: dict[str, t.Any] = {"calls": []}
    source = compile(
        textwrap.dedent(
            """\
            def marker():
                calls.append("evaluated")
                return int

            class Deferred:
                value: marker()
            """
        ),
        "<deferred-annotation>",
        "exec",
        dont_inherit=True,
    )
    exec(source, namespace)
    calls = t.cast("list[str]", namespace["calls"])
    deferred = t.cast("type", namespace["Deferred"])

    assert calls == []
    assert _own_annotations(deferred) == {}
    assert calls == []


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


    @dataclasses.dataclass(slots=True)
    class Gauge:
        """A gauge whose fields live in slots.

        Attributes
        ----------
        reading : int
            Most recent reading.
        scale : int
            Multiplier applied to the reading.
        """

        reading: int
        scale: int = 1


    class IntegerField:
        def __get__(self, obj, owner=None):
            if obj is None:
                return 0
            return vars(obj).get("_level", 0)

        def __set__(self, obj, value):
            vars(obj)["_level"] = value


    @dataclasses.dataclass
    class DescriptorGauge:
        """A gauge whose field is backed by a descriptor.

        Attributes
        ----------
        level : int
            Current descriptor-backed level.
        """

        level: int = IntegerField()


    class Outer:
        """A namespace for related records."""

        class NestedPoint(t.NamedTuple):
            """A point nested under another class.

            Attributes
            ----------
            x : int
                Nested horizontal offset.
            """

            x: int


    class InitDocumented:
        """A value whose initializer supplies its field documentation."""

        value: int

        def __init__(self, value: int) -> None:
            """Initialize the value.

            Attributes
            ----------
            value : int
                Initializer-owned field documentation.
            """
            self.value = value


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

    .. autoclass:: documented_fields_demo.Gauge

    .. autoclass:: documented_fields_demo.DescriptorGauge

    .. autoclass:: documented_fields_demo.Outer.NestedPoint

    .. autoclass:: documented_fields_demo.InitDocumented
       :class-doc-from: init

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
def test_documented_slotted_dataclass_fields_keep_their_descriptions(
    documented_fields_html_result: SharedSphinxResult,
) -> None:
    """A field held in a slot is described once, with or without a default."""
    attributes = _attribute_names(documented_fields_html_result)

    assert attributes.count("Gauge.reading") == 1
    assert attributes.count("Gauge.scale") == 1
    assert "Multiplier applied to the reading." in read_output(
        documented_fields_html_result, "index.html"
    )


@pytest.mark.integration
def test_documented_descriptor_dataclass_field_keeps_its_description(
    documented_fields_html_result: SharedSphinxResult,
) -> None:
    """A descriptor-backed dataclass field is described once."""
    attributes = _attribute_names(documented_fields_html_result)

    assert attributes.count("DescriptorGauge.level") == 1
    assert "Current descriptor-backed level." in read_output(
        documented_fields_html_result, "index.html"
    )


@pytest.mark.integration
def test_documented_nested_class_field_keeps_its_description(
    documented_fields_html_result: SharedSphinxResult,
) -> None:
    """A nested class field is described once."""
    attributes = _attribute_names(documented_fields_html_result)

    assert attributes.count("NestedPoint.x") == 1
    assert "Nested horizontal offset." in read_output(
        documented_fields_html_result, "index.html"
    )


@pytest.mark.integration
def test_initializer_attributes_are_described_once(
    documented_fields_html_result: SharedSphinxResult,
) -> None:
    """``class-doc-from=init`` follows the processed initializer docstring."""
    attributes = _attribute_names(documented_fields_html_result)

    assert attributes.count("InitDocumented.value") == 1
    assert "Initializer-owned field documentation." in read_output(
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

    import dataclasses
    import typing as t


    class Facade:
        """A facade over registered backends.

        Attributes
        ----------
        registry : dict[str, str]
            Backends registered so far.
        quoted_registry : dict[str, str]
            Backends registered through an explicitly quoted ClassVar.
        summary : str
            One-line description of the registry.
        """

        registry: t.ClassVar[dict[str, str]] = {}
        quoted_registry: "t.ClassVar[dict[str, str]]" = {}

        @property
        def summary(self) -> str:
            """Return how many backends are registered."""
            return f"{len(self.registry)} backends"


    class AnnotatedMethod:
        """A facade with an annotation retained for a same-named method.

        Attributes
        ----------
        action : Callable[[], str]
            Action advertised by the facade.
        """

        action: t.Callable[[], str]

        def action(self) -> str:
            """Return the action result."""
            return "done"


    @dataclasses.dataclass(slots=True)
    class Gauge:
        """A gauge whose fields live in slots.

        Attributes
        ----------
        reading : int
            Most recent reading.
        doubled : int
            The reading multiplied by two.
        """

        reading: int

        @property
        def doubled(self) -> int:
            """Return the reading multiplied by two."""
            return self.reading * 2
    '''
)

_NON_FIELD_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    .. autoclass:: non_field_members_demo.Facade

    .. autoclass:: non_field_members_demo.AnnotatedMethod

    .. autoclass:: non_field_members_demo.Gauge
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

    assert ("property", "Facade.summary") in [
        (member.objtype, member.fullname) for member in members
    ]
    assert "Return how many backends are registered." in read_output(
        non_field_members_html_result, "index.html"
    )


@pytest.mark.integration
def test_slotted_property_named_in_attributes_still_renders(
    non_field_members_html_result: SharedSphinxResult,
) -> None:
    """Holding fields in slots does not make a property one of them."""
    members = _described_members(get_doctree(non_field_members_html_result, "index"))

    assert ("property", "Gauge.doubled") in [
        (member.objtype, member.fullname) for member in members
    ]
    assert [member.fullname for member in members].count("Gauge.reading") == 1


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


@pytest.mark.integration
def test_quoted_classvar_named_in_attributes_still_renders(
    non_field_members_html_result: SharedSphinxResult,
) -> None:
    """An explicitly quoted ClassVar keeps its autodoc-rendered value."""
    members = _described_members(get_doctree(non_field_members_html_result, "index"))

    assert [
        member.signature
        for member in members
        if member.fullname == "Facade.quoted_registry" and "{}" in member.signature
    ] == ["quoted_registry: ClassVar[dict[str, str]] = {}"]


@pytest.mark.integration
def test_annotated_same_name_method_still_renders(
    non_field_members_html_result: SharedSphinxResult,
) -> None:
    """An annotation does not turn a same-named method into a field."""
    members = _described_members(get_doctree(non_field_members_html_result, "index"))

    assert ("method", "AnnotatedMethod.action") in [
        (member.objtype, member.fullname) for member in members
    ]
    assert "Return the action result." in read_output(
        non_field_members_html_result, "index.html"
    )


_FILTERED_DOCSTRING_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx.ext.autodoc",
        "sphinx_autodoc_typehints_gp",
        "remove_attributes",
    ]
    autodoc_default_options = {"members": True, "undoc-members": True}
    """
)

_REMOVE_ATTRIBUTES_SOURCE = textwrap.dedent(
    """\
    def remove_attributes(app, what, name, obj, options, lines):
        if what == "class" and name == "filtered_docstring_demo.Filtered":
            lines[:] = ["Replacement class documentation."]


    def setup(app):
        app.connect("autodoc-process-docstring", remove_attributes)
        return {"parallel_read_safe": True}
    """
)

_FILTERED_DOCSTRING_MODULE_SOURCE = textwrap.dedent(
    '''\
    from __future__ import annotations


    class Filtered:
        """A class whose Attributes section is removed before rendering.

        Attributes
        ----------
        value : int
            Documentation that a later processor removes.
        """

        value: int
    '''
)


@pytest.fixture(scope="module")
def filtered_docstring_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a project with a later docstring processor."""
    cache_root = tmp_path_factory.mktemp("filtered-docstring-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile(
                "conf.py",
                _FILTERED_DOCSTRING_CONF_PY.replace(
                    "__SCENARIO_SRCDIR__",
                    SCENARIO_SRCDIR_TOKEN,
                ),
                substitute_srcdir=True,
            ),
            ScenarioFile("remove_attributes.py", _REMOVE_ATTRIBUTES_SOURCE),
            ScenarioFile(
                "filtered_docstring_demo.py",
                _FILTERED_DOCSTRING_MODULE_SOURCE,
            ),
            ScenarioFile(
                "index.rst",
                "Demo\n====\n\n.. autoclass:: filtered_docstring_demo.Filtered\n",
            ),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("filtered_docstring_demo", "remove_attributes"),
    )


@pytest.mark.integration
def test_removed_attributes_section_leaves_autodoc_field(
    filtered_docstring_html_result: SharedSphinxResult,
) -> None:
    """The skip decision follows the final processed docstring."""
    attributes = _attribute_names(filtered_docstring_html_result)

    assert attributes.count("Filtered.value") == 1
    assert "Replacement class documentation." in read_output(
        filtered_docstring_html_result,
        "index.html",
    )
