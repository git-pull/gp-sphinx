"""Unit tests for sphinx_autodoc_typehints_gp helpers."""

from __future__ import annotations

import types
import typing as t

import pytest
from docutils import nodes
from sphinx import addnodes

import sphinx_autodoc_typehints_gp.rendering as sphinx_typehints_rendering
from sphinx_autodoc_typehints_gp import (
    AnnotationDisplay,
    build_annotation_display_paragraph,
    build_annotation_paragraph,
    build_resolved_annotation_display_paragraph,
    build_resolved_annotation_paragraph,
    classify_annotation_display,
    normalize_annotation_text,
    normalize_type_collection_text,
    render_annotation_nodes,
)
from sphinx_autodoc_typehints_gp._numpy_docstring import (
    _escape_args_and_kwargs,
    _partition_on_colon,
    process_numpy_docstring,
)
from sphinx_autodoc_typehints_gp.extension import (
    get_module_imports,
    resolve_annotation_string,
)

# ---------------------------------------------------------------------------
# get_module_imports / resolve_annotation_string  (individual — not fixture-based)
# ---------------------------------------------------------------------------


def test_get_module_imports_finds_typing_aliases() -> None:
    """get_module_imports extracts typing aliases from a module."""
    import sphinx.util.typing  # noqa: F401

    aliases = get_module_imports("sphinx.util.typing")
    assert "Any" in aliases
    assert aliases["Any"] == "typing.Any"


def test_get_module_imports_cached_on_repeat_call() -> None:
    """get_module_imports returns the same dict object on repeat calls."""
    import sphinx.util.typing  # noqa: F401

    first = get_module_imports("sphinx.util.typing")
    second = get_module_imports("sphinx.util.typing")
    assert first is second


def test_get_module_imports_missing_module_returns_empty() -> None:
    """get_module_imports returns empty dict for an unknown module name."""
    result = get_module_imports("__nonexistent_module__")
    assert result == {}


def test_normalize_annotation_text_qualifies_unresolved_names() -> None:
    """normalize_annotation_text can qualify unresolved forward refs."""
    result = normalize_annotation_text(
        "Session",
        module_name="libtmux.session",
        qualify_unresolved=True,
    )
    assert result == "libtmux.session.Session"


def test_normalize_type_collection_text_uses_default_type() -> None:
    """normalize_type_collection_text falls back to the default value type."""
    result = normalize_type_collection_text((), default={"theme": "mint"})
    assert result == "dict"


def test_normalize_annotation_text_can_collapse_literal_members() -> None:
    """normalize_annotation_text can flatten Literal[...] displays."""
    result = normalize_annotation_text(
        "Literal['open', 'closed']",
        collapse_literal=True,
    )
    assert result == "'open', 'closed'"


def test_classify_annotation_display_marks_literal_unions_as_enums() -> None:
    """Literal-only displays are classified as enum-like output."""
    display = classify_annotation_display("Literal['open', 'closed']")

    assert display == AnnotationDisplay(
        text="'open', 'closed'",
        is_literal_enum=True,
        literal_members=("'open'", "'closed'"),
    )


def test_classify_annotation_display_strips_none_before_classifying() -> None:
    """Optional annotations are not misclassified after stripping ``None``."""
    display = classify_annotation_display("str | None", strip_none=True)

    assert display.text == "str"
    assert display.is_literal_enum is False
    assert display.literal_members == ()


def test_render_annotation_nodes_delegates_to_private_parser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """render_annotation_nodes passes normalized text to the shared parser."""
    seen: dict[str, str] = {}

    def _fake_annotation_to_nodes(
        annotation: str,
        env: object,
    ) -> list[nodes.Node]:
        del env
        seen["annotation"] = annotation
        return [nodes.literal("", annotation)]

    monkeypatch.setattr(
        sphinx_typehints_rendering,
        "_annotation_to_nodes",
        _fake_annotation_to_nodes,
    )

    rendered = render_annotation_nodes(
        "Session",
        t.cast("t.Any", object()),
        module_name="libtmux.session",
        qualify_unresolved=True,
    )

    assert seen["annotation"] == "libtmux.session.Session"
    assert rendered[0].astext() == "libtmux.session.Session"


def test_build_annotation_paragraph_wraps_rendered_nodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """build_annotation_paragraph returns a paragraph around shared nodes."""

    def _fake_render_annotation_nodes(
        annotation: t.Any,
        env: object,
        *,
        strip_none: bool = False,
        collapse_literal: bool = False,
        module_name: str | None = None,
        aliases: dict[str, str] | None = None,
        qualify_unresolved: bool = False,
    ) -> list[nodes.Node]:
        del (
            annotation,
            env,
            strip_none,
            collapse_literal,
            module_name,
            aliases,
            qualify_unresolved,
        )
        return [nodes.literal("", "Server")]

    monkeypatch.setattr(
        sphinx_typehints_rendering,
        "render_annotation_nodes",
        _fake_render_annotation_nodes,
    )

    paragraph = build_annotation_paragraph("Server", t.cast("t.Any", object()))

    assert isinstance(paragraph, nodes.paragraph)
    assert paragraph.astext() == "Server"


def test_build_annotation_display_paragraph_marks_literal_unions_as_enum() -> None:
    """Literal-only displays use the compact shared enum marker."""
    paragraph = build_annotation_display_paragraph(
        "Literal['open', 'closed']",
        None,
    )

    assert isinstance(paragraph, nodes.paragraph)
    assert len(paragraph.children) == 1
    assert isinstance(paragraph.children[0], nodes.literal)
    assert paragraph.astext() == "enum"


def test_build_annotation_display_paragraph_delegates_for_non_enum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-enum displays still use the shared annotation paragraph builder."""
    seen: dict[str, str] = {}

    def _fake_build_annotation_paragraph(
        annotation: t.Any,
        env: object,
        *,
        strip_none: bool = False,
        collapse_literal: bool = False,
        module_name: str | None = None,
        aliases: dict[str, str] | None = None,
        qualify_unresolved: bool = False,
    ) -> nodes.paragraph:
        del (
            env,
            strip_none,
            collapse_literal,
            module_name,
            aliases,
            qualify_unresolved,
        )
        seen["annotation"] = t.cast(str, annotation)
        return nodes.paragraph("", "Server")

    monkeypatch.setattr(
        sphinx_typehints_rendering,
        "build_annotation_paragraph",
        _fake_build_annotation_paragraph,
    )

    paragraph = build_annotation_display_paragraph(
        "Server",
        t.cast("t.Any", object()),
    )

    assert seen["annotation"] == "Server"
    assert paragraph.astext() == "Server"


def test_build_annotation_display_paragraph_uses_literal_fallback_without_env() -> None:
    """The shared display helper stays safe without a live Sphinx env."""
    paragraph = build_annotation_display_paragraph("Server", None)

    assert isinstance(paragraph.children[0], nodes.literal)
    assert paragraph.astext() == "Server"


def test_render_annotation_nodes_downgrades_none_pending_xref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """render_annotation_nodes turns unresolved ``None`` xrefs into literals."""

    def _fake_annotation_to_nodes(
        annotation: str,
        env: object,
    ) -> list[nodes.Node]:
        del annotation, env
        return [
            addnodes.pending_xref(
                "",
                nodes.Text("None"),
                refdomain="py",
                reftype="class",
                reftarget="None",
            )
        ]

    monkeypatch.setattr(
        sphinx_typehints_rendering,
        "_annotation_to_nodes",
        _fake_annotation_to_nodes,
    )

    rendered = render_annotation_nodes("None", t.cast("t.Any", object()))

    assert len(rendered) == 1
    assert isinstance(rendered[0], nodes.literal)
    assert rendered[0].astext() == "None"


def test_build_resolved_annotation_paragraph_resolves_pending_xrefs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late-added annotation nodes are resolved before HTML writing."""

    class _DummyEnv:
        def resolve_references(
            self,
            doctree: nodes.document,
            docname: str,
            builder: object,
        ) -> None:
            del docname, builder
            pending = t.cast(addnodes.pending_xref, doctree.children[0].children[0])
            paragraph = t.cast(nodes.paragraph, doctree.children[0])
            paragraph[0] = nodes.literal("", pending.astext())

    app = t.cast(
        "t.Any",
        types.SimpleNamespace(
            env=_DummyEnv(),
            builder=object(),
        ),
    )

    def _fake_build_annotation_paragraph(
        annotation: t.Any,
        env: object,
        *,
        strip_none: bool = False,
        collapse_literal: bool = False,
        module_name: str | None = None,
        aliases: dict[str, str] | None = None,
        qualify_unresolved: bool = False,
    ) -> nodes.paragraph:
        del (
            annotation,
            env,
            strip_none,
            collapse_literal,
            module_name,
            aliases,
            qualify_unresolved,
        )
        paragraph = nodes.paragraph()
        paragraph += addnodes.pending_xref(
            "",
            nodes.Text("None"),
            refdomain="py",
            reftype="class",
            reftarget="None",
        )
        return paragraph

    monkeypatch.setattr(
        sphinx_typehints_rendering,
        "build_annotation_paragraph",
        _fake_build_annotation_paragraph,
    )
    paragraph = build_resolved_annotation_paragraph("None", app, "index")

    assert isinstance(paragraph, nodes.paragraph)
    assert isinstance(paragraph.children[0], nodes.literal)
    assert paragraph.astext() == "None"


def test_build_resolved_annotation_display_paragraph_marks_literal_unions_as_enum() -> (
    None
):
    """Literal-only displays do not try to late-resolve shared enum markers."""
    paragraph = build_resolved_annotation_display_paragraph(
        "Literal['open', 'closed']",
        t.cast("t.Any", object()),
        "index",
    )

    assert isinstance(paragraph, nodes.paragraph)
    assert isinstance(paragraph.children[0], nodes.literal)
    assert paragraph.astext() == "enum"


def test_build_resolved_annotation_display_paragraph_delegates_for_non_enum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolved non-enum displays still use the shared resolved builder."""
    seen: dict[str, str] = {}

    def _fake_build_resolved_annotation_paragraph(
        annotation: t.Any,
        app: object,
        docname: str,
        *,
        strip_none: bool = False,
        collapse_literal: bool = False,
        module_name: str | None = None,
        aliases: dict[str, str] | None = None,
        qualify_unresolved: bool = False,
    ) -> nodes.paragraph:
        del (
            app,
            docname,
            strip_none,
            collapse_literal,
            module_name,
            aliases,
            qualify_unresolved,
        )
        seen["annotation"] = t.cast(str, annotation)
        return nodes.paragraph("", "Server")

    monkeypatch.setattr(
        sphinx_typehints_rendering,
        "build_resolved_annotation_paragraph",
        _fake_build_resolved_annotation_paragraph,
    )

    paragraph = build_resolved_annotation_display_paragraph(
        "Server",
        t.cast("t.Any", object()),
        "index",
    )

    assert seen["annotation"] == "Server"
    assert paragraph.astext() == "Server"


def test_numpy_empty_docstring() -> None:
    """Empty docstring produces empty output."""
    assert process_numpy_docstring([]) == []


def test_numpy_no_sections() -> None:
    """Docstring without NumPy sections passes through unchanged."""
    lines = ["Just a summary.", "", "Extended description."]
    assert process_numpy_docstring(lines) == lines


def test_numpy_full_docstring() -> None:
    """Complete multi-section docstring parses all sections correctly."""
    lines = [
        "Do something important.",
        "",
        "Extended description goes here.",
        "",
        "Parameters",
        "----------",
        "name : str",
        "    The name.",
        "count : int",
        "    The count.",
        "",
        "Returns",
        "-------",
        "bool",
        "    True if successful.",
        "",
        "Raises",
        "------",
        "ValueError",
        "    If name is empty.",
        "",
        "Examples",
        "--------",
        ">>> do_something('foo', 3)",
        "True",
    ]
    result = process_numpy_docstring(lines)
    joined = "\n".join(result)
    assert "Do something important." in joined
    assert "Extended description goes here." in joined
    assert ":param name: The name." in joined
    assert ":type name: str" in joined
    assert ":param count: The count." in joined
    assert ":type count: int" in joined
    assert ":returns: True if successful." in joined
    assert ":rtype: bool" in joined
    assert ":raises ValueError:" in joined
    assert ".. rubric:: Examples" in joined
    assert ">>> do_something('foo', 3)" in joined


# ---------------------------------------------------------------------------
# resolve_annotation_string — parametrized
# ---------------------------------------------------------------------------


class ResolveAnnotationFixture(t.NamedTuple):
    """Fixture for resolve_annotation_string cases."""

    test_id: str
    ann_str: str
    module_name: str
    aliases: dict[str, str]
    expected: str


_RESOLVE_FIXTURES: list[ResolveAnnotationFixture] = [
    ResolveAnnotationFixture(
        test_id="qualified_names",
        ann_str="List[MyClass]",
        module_name="my_module",
        aliases={"List": "typing.List", "MyClass": "other.MyClass"},
        expected="~typing.List[~other.MyClass]",
    ),
    ResolveAnnotationFixture(
        test_id="local_class",
        ann_str="List[LocalClass]",
        module_name="my_module",
        aliases={"List": "typing.List"},
        expected="~typing.List[~my_module.LocalClass]",
    ),
    ResolveAnnotationFixture(
        test_id="builtin_unchanged",
        ann_str="List[str]",
        module_name="my_module",
        aliases={"List": "typing.List"},
        expected="~typing.List[str]",
    ),
    ResolveAnnotationFixture(
        test_id="syntax_error_returns_original",
        ann_str="not valid[python]syntax!!!",
        module_name="mod",
        aliases={},
        expected="not valid[python]syntax!!!",
    ),
]


@pytest.mark.parametrize(
    list(ResolveAnnotationFixture._fields),
    _RESOLVE_FIXTURES,
    ids=[f.test_id for f in _RESOLVE_FIXTURES],
)
def test_resolve_annotation_string(
    test_id: str,
    ann_str: str,
    module_name: str,
    aliases: dict[str, str],
    expected: str,
) -> None:
    """resolve_annotation_string converts annotation strings correctly."""
    assert resolve_annotation_string(ann_str, module_name, aliases) == expected


# ---------------------------------------------------------------------------
# _partition_on_colon — parametrized
# ---------------------------------------------------------------------------


class PartitionFixture(t.NamedTuple):
    """Fixture for _partition_on_colon cases."""

    test_id: str
    line: str
    expected: tuple[str, str, str]


_PARTITION_FIXTURES: list[PartitionFixture] = [
    PartitionFixture(
        test_id="basic_name_type",
        line="name : int",
        expected=("name", ":", "int"),
    ),
    PartitionFixture(
        test_id="no_colon",
        line="name",
        expected=("name", "", ""),
    ),
    PartitionFixture(
        test_id="xref_colon_preserved",
        line=":class:`Foo` : bar",
        expected=(":class:`Foo`", ":", "bar"),
    ),
]


@pytest.mark.parametrize(
    list(PartitionFixture._fields),
    _PARTITION_FIXTURES,
    ids=[f.test_id for f in _PARTITION_FIXTURES],
)
def test_partition_on_colon(
    test_id: str,
    line: str,
    expected: tuple[str, str, str],
) -> None:
    """_partition_on_colon splits on the first bare colon outside xrefs."""
    assert _partition_on_colon(line) == expected


# ---------------------------------------------------------------------------
# _escape_args_and_kwargs — parametrized
# ---------------------------------------------------------------------------


class EscapeFixture(t.NamedTuple):
    """Fixture for _escape_args_and_kwargs cases."""

    test_id: str
    name: str
    expected: str


_ESCAPE_FIXTURES: list[EscapeFixture] = [
    EscapeFixture(test_id="plain_name", name="x", expected="x"),
    EscapeFixture(test_id="single_star", name="*args", expected=r"\*args"),
    EscapeFixture(test_id="double_star", name="**kwargs", expected=r"\*\*kwargs"),
]


@pytest.mark.parametrize(
    list(EscapeFixture._fields),
    _ESCAPE_FIXTURES,
    ids=[f.test_id for f in _ESCAPE_FIXTURES],
)
def test_escape_args_and_kwargs(
    test_id: str,
    name: str,
    expected: str,
) -> None:
    """_escape_args_and_kwargs escapes RST special prefixes."""
    assert _escape_args_and_kwargs(name) == expected


# ---------------------------------------------------------------------------
# Parameters section — parametrized
# ---------------------------------------------------------------------------


class ParamSectionFixture(t.NamedTuple):
    """Fixture for Parameters section parsing cases."""

    test_id: str
    input_lines: list[str]
    expected_in_output: list[str]
    absent_from_output: list[str]


_PARAM_FIXTURES: list[ParamSectionFixture] = [
    ParamSectionFixture(
        test_id="basic_typed_params",
        input_lines=[
            "Summary.",
            "",
            "Parameters",
            "----------",
            "x : int",
            "    The x value.",
            "y : str",
            "    The y value.",
        ],
        expected_in_output=[
            ":param x: The x value.",
            ":type x: int",
            ":param y: The y value.",
            ":type y: str",
        ],
        absent_from_output=[],
    ),
    ParamSectionFixture(
        test_id="param_no_type",
        input_lines=[
            "Summary.",
            "",
            "Parameters",
            "----------",
            "x",
            "    The x value.",
        ],
        expected_in_output=[":param x: The x value."],
        absent_from_output=[":type x:"],
    ),
    ParamSectionFixture(
        test_id="star_args_escaped",
        input_lines=[
            "Summary.",
            "",
            "Parameters",
            "----------",
            "*args : str",
            "    Positional args.",
            "**kwargs : int",
            "    Keyword args.",
        ],
        expected_in_output=[r":param \*args:", r":param \*\*kwargs:"],
        absent_from_output=[],
    ),
    ParamSectionFixture(
        test_id="multiline_desc_indented",
        input_lines=[
            "Summary.",
            "",
            "Parameters",
            "----------",
            "x : int",
            "    Line one.",
            "    Line two.",
        ],
        expected_in_output=[":param x: Line one.", "          Line two."],
        absent_from_output=[],
    ),
]


@pytest.mark.parametrize(
    list(ParamSectionFixture._fields),
    _PARAM_FIXTURES,
    ids=[f.test_id for f in _PARAM_FIXTURES],
)
def test_numpy_parameters_section(
    test_id: str,
    input_lines: list[str],
    expected_in_output: list[str],
    absent_from_output: list[str],
) -> None:
    """Parameters section produces correct :param: and :type: fields."""
    result = process_numpy_docstring(input_lines)
    joined = "\n".join(result)
    for fragment in expected_in_output:
        assert fragment in joined, f"[{test_id}] Missing: {fragment!r}"
    for fragment in absent_from_output:
        assert fragment not in joined, f"[{test_id}] Unexpected: {fragment!r}"


# ---------------------------------------------------------------------------
# Returns section — parametrized
# ---------------------------------------------------------------------------


class ReturnSectionFixture(t.NamedTuple):
    """Fixture for Returns section parsing cases."""

    test_id: str
    input_lines: list[str]
    expected_in_output: list[str]


_RETURN_FIXTURES: list[ReturnSectionFixture] = [
    ReturnSectionFixture(
        test_id="single_typed_return",
        input_lines=[
            "Summary.",
            "",
            "Returns",
            "-------",
            "bool",
            "    True if ok.",
        ],
        expected_in_output=[":returns: True if ok.", ":rtype: bool"],
    ),
    ReturnSectionFixture(
        test_id="named_typed_return",
        input_lines=[
            "Summary.",
            "",
            "Returns",
            "-------",
            "result : bool",
            "    True if ok.",
        ],
        expected_in_output=[":returns:", ":rtype: bool"],
    ),
    ReturnSectionFixture(
        test_id="multiple_returns_bullet_format",
        input_lines=[
            "Summary.",
            "",
            "Returns",
            "-------",
            "x : int",
            "    X val.",
            "y : str",
            "    Y val.",
        ],
        expected_in_output=[":returns: *"],
    ),
]


@pytest.mark.parametrize(
    list(ReturnSectionFixture._fields),
    _RETURN_FIXTURES,
    ids=[f.test_id for f in _RETURN_FIXTURES],
)
def test_numpy_returns_section(
    test_id: str,
    input_lines: list[str],
    expected_in_output: list[str],
) -> None:
    """Returns section produces correct :returns: and :rtype: fields."""
    result = process_numpy_docstring(input_lines)
    joined = "\n".join(result)
    for fragment in expected_in_output:
        assert fragment in joined, f"[{test_id}] Missing: {fragment!r}"


# ---------------------------------------------------------------------------
# Raises section — parametrized
# ---------------------------------------------------------------------------


class RaisesSectionFixture(t.NamedTuple):
    """Fixture for Raises section parsing cases."""

    test_id: str
    input_lines: list[str]
    expected_in_output: list[str]


_RAISES_FIXTURES: list[RaisesSectionFixture] = [
    RaisesSectionFixture(
        test_id="basic_raises",
        input_lines=[
            "Summary.",
            "",
            "Raises",
            "------",
            "ValueError",
            "    If x is negative.",
        ],
        expected_in_output=[":raises ValueError:", "If x is negative."],
    ),
    RaisesSectionFixture(
        test_id="raises_without_desc",
        input_lines=[
            "Summary.",
            "",
            "Raises",
            "------",
            "TypeError",
            "",
        ],
        expected_in_output=[":raises TypeError:"],
    ),
    RaisesSectionFixture(
        test_id="raises_with_exc_role",
        input_lines=[
            "Summary.",
            "",
            "Raises",
            "------",
            ":exc:`exc.LibTmuxException`",
        ],
        expected_in_output=[":raises exc.LibTmuxException:"],
    ),
    RaisesSectionFixture(
        test_id="raises_multiple_comma_roles",
        input_lines=[
            "Summary.",
            "",
            "Raises",
            "------",
            ":exc:`exc.OptionError`, :exc:`exc.UnknownOption`,",
            ":exc:`exc.InvalidOption`",
        ],
        expected_in_output=[
            ":raises exc.OptionError:",
            ":raises exc.UnknownOption:",
            ":raises exc.InvalidOption:",
        ],
    ),
    RaisesSectionFixture(
        test_id="raises_with_tilde_role",
        input_lines=[
            "Summary.",
            "",
            "Raises",
            "------",
            ":exc:`~pkg.mod.MyErr`",
        ],
        expected_in_output=[":raises MyErr:"],
    ),
    RaisesSectionFixture(
        test_id="raises_with_bracketed_generic",
        input_lines=[
            "Summary.",
            "",
            "Raises",
            "------",
            "Dict[str, MyErr]",
        ],
        expected_in_output=[":raises Dict[str, MyErr]:"],
    ),
]


@pytest.mark.parametrize(
    list(RaisesSectionFixture._fields),
    _RAISES_FIXTURES,
    ids=[f.test_id for f in _RAISES_FIXTURES],
)
def test_numpy_raises_section(
    test_id: str,
    input_lines: list[str],
    expected_in_output: list[str],
) -> None:
    """Raises section produces correct :raises Type: fields."""
    result = process_numpy_docstring(input_lines)
    joined = "\n".join(result)
    for fragment in expected_in_output:
        assert fragment in joined, f"[{test_id}] Missing: {fragment!r}"


# ---------------------------------------------------------------------------
# Generic sections (Examples, Notes, Yields, References) — parametrized
# ---------------------------------------------------------------------------


class GenericSectionFixture(t.NamedTuple):
    """Fixture for generic section parsing cases."""

    test_id: str
    input_lines: list[str]
    expected_in_output: list[str]


_GENERIC_SECTION_FIXTURES: list[GenericSectionFixture] = [
    GenericSectionFixture(
        test_id="examples_rubric",
        input_lines=[
            "Summary.",
            "",
            "Examples",
            "--------",
            ">>> func(1)",
            "True",
        ],
        expected_in_output=[".. rubric:: Examples", ">>> func(1)"],
    ),
    GenericSectionFixture(
        test_id="notes_rubric",
        input_lines=[
            "Summary.",
            "",
            "Notes",
            "-----",
            "Some notes here.",
        ],
        expected_in_output=[".. rubric:: Notes", "Some notes here."],
    ),
    GenericSectionFixture(
        test_id="references_rubric",
        input_lines=[
            "Summary.",
            "",
            "References",
            "----------",
            ".. [1] Author, Title.",
        ],
        expected_in_output=[".. rubric:: References"],
    ),
    GenericSectionFixture(
        test_id="yields_section",
        input_lines=[
            "Summary.",
            "",
            "Yields",
            "------",
            "int",
            "    Next value.",
        ],
        expected_in_output=[":Yields:", "int"],
    ),
]


@pytest.mark.parametrize(
    list(GenericSectionFixture._fields),
    _GENERIC_SECTION_FIXTURES,
    ids=[f.test_id for f in _GENERIC_SECTION_FIXTURES],
)
def test_numpy_generic_section(
    test_id: str,
    input_lines: list[str],
    expected_in_output: list[str],
) -> None:
    """Generic sections (Examples, Notes, Yields, References) render correctly."""
    result = process_numpy_docstring(input_lines)
    joined = "\n".join(result)
    for fragment in expected_in_output:
        assert fragment in joined, f"[{test_id}] Missing: {fragment!r}"


class GenericSectionEmptyFixture(t.NamedTuple):
    """Fixture for empty/stub generic section behavior."""

    test_id: str
    input_lines: list[str]
    rubric: str
    should_emit: bool


_GENERIC_EMPTY_FIXTURES: list[GenericSectionEmptyFixture] = [
    GenericSectionEmptyFixture(
        test_id="notes_empty_content",
        input_lines=[
            "Summary.",
            "",
            "Notes",
            "-----",
        ],
        rubric=".. rubric:: Notes",
        should_emit=False,
    ),
    GenericSectionEmptyFixture(
        test_id="notes_only_todo",
        input_lines=[
            "Summary.",
            "",
            "Notes",
            "-----",
            ".. todo::",
            "",
            "    assure it works.",
        ],
        rubric=".. rubric:: Notes",
        should_emit=False,
    ),
    GenericSectionEmptyFixture(
        test_id="examples_empty_keeps_rubric",
        input_lines=[
            "Summary.",
            "",
            "Examples",
            "--------",
        ],
        rubric=".. rubric:: Examples",
        should_emit=True,
    ),
    GenericSectionEmptyFixture(
        test_id="references_empty_keeps_rubric",
        input_lines=[
            "Summary.",
            "",
            "References",
            "----------",
        ],
        rubric=".. rubric:: References",
        should_emit=True,
    ),
    GenericSectionEmptyFixture(
        test_id="examples_only_todo_keeps_rubric",
        input_lines=[
            "Summary.",
            "",
            "Examples",
            "--------",
            ".. todo::",
            "",
            "    write me",
        ],
        rubric=".. rubric:: Examples",
        should_emit=True,
    ),
]


@pytest.mark.parametrize(
    list(GenericSectionEmptyFixture._fields),
    _GENERIC_EMPTY_FIXTURES,
    ids=[f.test_id for f in _GENERIC_EMPTY_FIXTURES],
)
def test_numpy_generic_section_empty(
    test_id: str,
    input_lines: list[str],
    rubric: str,
    should_emit: bool,
) -> None:
    """Empty Notes drops its rubric; other generic sections keep theirs."""
    result = process_numpy_docstring(input_lines)
    joined = "\n".join(result)
    if should_emit:
        assert rubric in joined, f"[{test_id}] Expected rubric {rubric!r} to be emitted"
    else:
        assert rubric not in joined, (
            f"[{test_id}] Empty rubric {rubric!r} should not be emitted"
        )


# ---------------------------------------------------------------------------
# Special sections (See Also, Attributes, Admonitions) — parametrized
# ---------------------------------------------------------------------------


class SpecialSectionFixture(t.NamedTuple):
    """Fixture for special section parsing cases."""

    test_id: str
    input_lines: list[str]
    expected_in_output: list[str]


_SPECIAL_SECTION_FIXTURES: list[SpecialSectionFixture] = [
    SpecialSectionFixture(
        test_id="see_also_bare_name",
        input_lines=[
            "Summary.",
            "",
            "See Also",
            "--------",
            "other_func",
        ],
        expected_in_output=[".. seealso::", ":py:obj:`other_func`"],
    ),
    SpecialSectionFixture(
        test_id="see_also_with_desc",
        input_lines=[
            "Summary.",
            "",
            "See Also",
            "--------",
            "other_func : Related function.",
        ],
        expected_in_output=[".. seealso::", ":py:obj:`other_func`"],
    ),
    SpecialSectionFixture(
        test_id="see_also_comma_separated",
        input_lines=[
            "Summary.",
            "",
            "See Also",
            "--------",
            "func1, func2",
        ],
        expected_in_output=[
            ".. seealso::",
            ":py:obj:`func1`",
            ":py:obj:`func2`",
        ],
    ),
    SpecialSectionFixture(
        test_id="see_also_role_ref",
        input_lines=[
            "Summary.",
            "",
            "See Also",
            "--------",
            ":func:`pkg.func` : Does things.",
        ],
        expected_in_output=[".. seealso::", ":func:`pkg.func`"],
    ),
    SpecialSectionFixture(
        test_id="see_also_comma_roles",
        input_lines=[
            "Summary.",
            "",
            "See Also",
            "--------",
            ":func:`func1`, :func:`func2`",
        ],
        expected_in_output=[
            ".. seealso::",
            ":func:`func1`",
            ":func:`func2`",
        ],
    ),
    SpecialSectionFixture(
        test_id="see_also_mixed_role_and_plain",
        input_lines=[
            "Summary.",
            "",
            "See Also",
            "--------",
            ":meth:`Widget.run` : Runs the widget.",
            "plain_func",
        ],
        expected_in_output=[
            ".. seealso::",
            ":meth:`Widget.run`",
            ":py:obj:`plain_func`",
        ],
    ),
    SpecialSectionFixture(
        test_id="attributes_section",
        input_lines=[
            "Summary.",
            "",
            "Attributes",
            "----------",
            "x : int",
            "    The x value.",
        ],
        expected_in_output=[".. attribute:: x", ":type: int"],
    ),
    SpecialSectionFixture(
        test_id="warning_admonition",
        input_lines=[
            "Summary.",
            "",
            "Warning",
            "-------",
            "Be careful.",
        ],
        expected_in_output=[".. warning::", "Be careful."],
    ),
    SpecialSectionFixture(
        test_id="note_admonition",
        input_lines=[
            "Summary.",
            "",
            "Note",
            "----",
            "This is a note.",
        ],
        expected_in_output=[".. note::"],
    ),
]


@pytest.mark.parametrize(
    list(SpecialSectionFixture._fields),
    _SPECIAL_SECTION_FIXTURES,
    ids=[f.test_id for f in _SPECIAL_SECTION_FIXTURES],
)
def test_numpy_special_section(
    test_id: str,
    input_lines: list[str],
    expected_in_output: list[str],
) -> None:
    """Special sections (See Also, Attributes, Admonitions) render correctly."""
    result = process_numpy_docstring(input_lines)
    joined = "\n".join(result)
    for fragment in expected_in_output:
        assert fragment in joined, f"[{test_id}] Missing: {fragment!r}"


# ---------------------------------------------------------------------------
# setup() event wiring
# ---------------------------------------------------------------------------


def test_setup_registers_builder_inited_cache_clearing() -> None:
    """setup() connects builder-inited to _clear_caches."""
    from sphinx.application import Sphinx

    from sphinx_autodoc_typehints_gp.extension import _clear_caches, setup

    connections: list[tuple[str, t.Any]] = []

    app = t.cast(
        Sphinx,
        types.SimpleNamespace(
            connect=lambda event, handler, **kw: connections.append((event, handler)),
        ),
    )

    setup(app)

    event_map = dict(connections)
    assert "builder-inited" in event_map
    assert event_map["builder-inited"] is _clear_caches
