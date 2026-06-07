"""Unit tests for the docutils component autodoc pipeline.

Covers per-type discovery, fact rows, and the shared
``normalize_component_nodes`` / ``inject_component_badges`` doctree
behavior. One file per package; each component type contributes its own
section as it lands.
"""

from __future__ import annotations

import typing as t

import pytest
from docutils import nodes
from docutils.transforms import Transform
from sphinx import addnodes

from sphinx_autodoc_docutils._badges import build_transform_badge_group
from sphinx_autodoc_docutils._components import (
    component_classes,
    component_markup,
    import_component,
    inject_component_badges,
    normalize_component_nodes,
)
from sphinx_autodoc_docutils._nodes_doc import (
    NodeInfo,
    _node_fact_rows,
    _nodes_from_calls,
    discover_node,
    discover_nodes,
    node_categories,
)
from sphinx_autodoc_docutils._parsers_doc import (
    ParserInfo,
    _parser_fact_rows,
    _source_parsers_from_calls,
    discover_parser,
    discover_parsers,
)
from sphinx_autodoc_docutils._readers_doc import (
    _reader_fact_rows,
    discover_reader,
    discover_readers,
)
from sphinx_autodoc_docutils._transforms_doc import (
    TransformInfo,
    _transform_fact_rows,
    _transforms_from_calls,
    discover_transform,
    discover_transforms,
)
from sphinx_autodoc_docutils._translators_doc import (
    TranslatorInfo,
    _translator_fact_rows,
    _translators_from_calls,
    discover_translator,
    discover_translators,
    translator_overrides,
)
from sphinx_autodoc_docutils._writers_doc import (
    _writer_fact_rows,
    discover_writer,
    discover_writers,
    resolve_translator_class,
)
from sphinx_ux_autodoc_layout import ApiFactRow
from sphinx_ux_autodoc_layout._nodes import api_component

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class _DemoTransform(Transform):
    """Demo transform that reorders nothing."""

    default_priority = 321

    def apply(self) -> None:
        """Do nothing; exists for metadata tests."""


class _BareTransform(Transform):
    """Demo transform without an explicit priority."""

    def apply(self) -> None:
        """Do nothing; exists for metadata tests."""


def _make_component_desc(
    objtype: str,
    *,
    name: str = "demo.DemoComponent",
) -> addnodes.desc:
    """Build a minimal docutils-domain desc node as Auto* would produce."""
    desc = addnodes.desc(domain="docutils", objtype=objtype)
    sig = addnodes.desc_signature(ids=[f"docutils-{objtype}-{name.lower()}"])
    sig += addnodes.desc_name("", name)
    desc += sig
    content = addnodes.desc_content()
    content += nodes.paragraph("", "A demo component for testing.")
    desc += content
    return desc


def _api_facts_child(content: addnodes.desc_content) -> api_component | None:
    """Return the gp-sphinx-api-facts component in desc_content, or None."""
    for child in content.children:
        if (
            isinstance(child, api_component)
            and child.get("name") == "gp-sphinx-api-facts"
        ):
            return child
    return None


def _facts_by_label(facts_section: api_component) -> dict[str, str]:
    """Return label -> body text for an gp-sphinx-api-facts section."""
    by_label: dict[str, str] = {}
    for field in facts_section.findall(nodes.field):
        if field.children:
            label = field.children[0].astext()
            body = field.children[1].astext() if len(field.children) > 1 else ""
            by_label[label] = body
    return by_label


def _demo_fact_rows() -> list[ApiFactRow]:
    """Return a small facts list for normalize tests."""
    paragraph = nodes.paragraph()
    paragraph += nodes.literal("demo", "demo")
    return [ApiFactRow("Python path", paragraph)]


# ---------------------------------------------------------------------------
# Shared pipeline
# ---------------------------------------------------------------------------


def test_component_markup_renders_domain_directive() -> None:
    """component_markup emits a docutils-domain object description."""
    markup = component_markup("transform", "pkg.Sanitize", "Strip stuff.")
    assert markup.splitlines()[0] == ".. docutils:transform:: pkg.Sanitize"
    assert "   Strip stuff." in markup


def test_component_markup_default_summary() -> None:
    """component_markup falls back to a generic summary."""
    markup = component_markup("writer", "pkg.W", "")
    assert "Autodocumented docutils writer." in markup


def test_normalize_component_inserts_api_facts_after_summary() -> None:
    """normalize_component_nodes inserts gp-sphinx-api-facts after the summary."""
    desc = _make_component_desc("transform")
    content = t.cast("addnodes.desc_content", desc.children[-1])

    normalize_component_nodes(
        [desc],
        objtype="transform",
        fact_rows=_demo_fact_rows(),
    )

    assert isinstance(content.children[0], nodes.paragraph)
    facts = _api_facts_child(content)
    assert facts is not None, "gp-sphinx-api-facts section should be inserted"
    assert "Python path" in _facts_by_label(facts)


def test_normalize_component_skips_other_objtypes() -> None:
    """normalize_component_nodes leaves non-matching objtypes untouched."""
    transform_desc = _make_component_desc("transform")
    writer_desc = _make_component_desc("writer")

    normalize_component_nodes(
        [transform_desc, writer_desc],
        objtype="transform",
        fact_rows=_demo_fact_rows(),
    )

    writer_content = t.cast("addnodes.desc_content", writer_desc.children[-1])
    assert _api_facts_child(writer_content) is None


def test_inject_component_badges_marks_signature() -> None:
    """inject_component_badges attaches the badge slot exactly once."""
    desc = _make_component_desc("transform")
    sig = t.cast("addnodes.desc_signature", desc.children[0])

    inject_component_badges(
        [desc],
        objtype="transform",
        badge_group=build_transform_badge_group(760),
    )

    assert sig.get("sadoc_badges_injected") is True


def test_inject_component_badges_skips_other_objtypes() -> None:
    """inject_component_badges leaves non-matching objtypes untouched."""
    desc = _make_component_desc("writer")
    sig = t.cast("addnodes.desc_signature", desc.children[0])

    inject_component_badges(
        [desc],
        objtype="transform",
        badge_group=build_transform_badge_group(None),
    )

    assert sig.get("sadoc_badges_injected") is None


def test_import_component_rejects_non_class() -> None:
    """import_component raises TypeError for non-class attributes."""
    with pytest.raises(TypeError, match="Expected a class"):
        import_component("docutils.transforms.misc.__doc__")


# ---------------------------------------------------------------------------
# Linked facts
# ---------------------------------------------------------------------------


def test_python_path_fact_is_linked() -> None:
    """The Python path fact wraps the dotted path in a py-obj xref."""
    rows = _transform_fact_rows(TransformInfo(cls=_DemoTransform))
    xref = next(iter(rows[0].body.findall(addnodes.pending_xref)))
    assert xref["refdomain"] == "py"
    assert xref["reftarget"].endswith("._DemoTransform")
    assert xref["refwarn"] is False


def test_reader_transforms_fact_links_qualified_targets() -> None:
    """Transform chips display bare names but target qualified paths."""
    from docutils.readers.standalone import Reader

    rows = _reader_fact_rows(Reader)
    transforms_row = next(row for row in rows if row.label == "Transforms")
    xrefs = list(transforms_row.body.findall(addnodes.pending_xref))
    assert xrefs
    targets = {xref["reftarget"] for xref in xrefs}
    assert "docutils.transforms.misc.Transitions" in targets
    displays = {xref.astext() for xref in xrefs}
    assert "Transitions" in displays


def test_translator_overrides_fact_links_methods() -> None:
    """Override chips target the fully-qualified method paths."""
    rows = _translator_fact_rows(TranslatorInfo(cls=_DemoVisitor))
    overrides_row = next(row for row in rows if row.label == "Overrides")
    prefix = f"{_DemoVisitor.__module__}.{_DemoVisitor.__qualname__}"
    targets = [
        xref["reftarget"] for xref in overrides_row.body.findall(addnodes.pending_xref)
    ]
    assert targets == [
        f"{prefix}.depart_paragraph",
        f"{prefix}.visit_paragraph",
    ]


def test_supported_formats_fact_renders_chips() -> None:
    """List-valued facts render one literal chip per value."""
    from docutils.writers import html5_polyglot

    rows = _writer_fact_rows(html5_polyglot.Writer)
    formats_row = next(row for row in rows if row.label == "Supported formats")
    literal_count = sum(
        isinstance(child, nodes.literal) for child in formats_row.body.children
    )
    assert literal_count == 3


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------


class TransformsFromCallsCase(t.NamedTuple):
    """Test case for _transforms_from_calls()."""

    test_id: str
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]]
    expected: list[tuple[str, str]]


_TRANSFORMS_FROM_CALLS_CASES: list[TransformsFromCallsCase] = [
    TransformsFromCallsCase(
        test_id="read_phase",
        calls=[("add_transform", (_DemoTransform,), {})],
        expected=[("_DemoTransform", "add_transform")],
    ),
    TransformsFromCallsCase(
        test_id="post_phase",
        calls=[("add_post_transform", (_DemoTransform,), {})],
        expected=[("_DemoTransform", "add_post_transform")],
    ),
    TransformsFromCallsCase(
        test_id="ignores_other_calls",
        calls=[
            ("add_directive", ("noise", object), {}),
            ("add_transform", (_DemoTransform,), {}),
        ],
        expected=[("_DemoTransform", "add_transform")],
    ),
    TransformsFromCallsCase(
        test_id="ignores_non_transform_classes",
        calls=[("add_transform", (object,), {})],
        expected=[],
    ),
    TransformsFromCallsCase(
        test_id="dedupes_same_phase",
        calls=[
            ("add_transform", (_DemoTransform,), {}),
            ("add_transform", (_DemoTransform,), {}),
        ],
        expected=[("_DemoTransform", "add_transform")],
    ),
    TransformsFromCallsCase(
        test_id="keeps_both_phases",
        calls=[
            ("add_transform", (_DemoTransform,), {}),
            ("add_post_transform", (_DemoTransform,), {}),
        ],
        expected=[
            ("_DemoTransform", "add_transform"),
            ("_DemoTransform", "add_post_transform"),
        ],
    ),
]


@pytest.mark.parametrize(
    "case",
    _TRANSFORMS_FROM_CALLS_CASES,
    ids=lambda c: c.test_id,
)
def test_transforms_from_calls(case: TransformsFromCallsCase) -> None:
    """_transforms_from_calls extracts transform registrations."""
    infos = _transforms_from_calls(case.calls)
    assert [(info.cls.__name__, info.registered_via) for info in infos] == case.expected


def test_discover_transforms_scan_fallback() -> None:
    """discover_transforms scans modules without a registering setup()."""
    infos = discover_transforms("docutils.transforms.misc")
    names = sorted(info.cls.__name__ for info in infos)
    assert names == ["CallBack", "ClassAttribute", "Transitions"]
    assert {info.registered_via for info in infos} == {""}


def test_discover_transforms_empty_for_module_without_transforms() -> None:
    """discover_transforms returns [] for modules without transforms."""
    assert discover_transforms("sphinx_fonts") == []


def test_discover_transform_single_path() -> None:
    """discover_transform imports one transform from a dotted path."""
    info = discover_transform("docutils.transforms.misc.Transitions")
    assert info.cls.__name__ == "Transitions"
    assert info.qualified_name == "docutils.transforms.misc.Transitions"


def test_component_classes_excludes_base() -> None:
    """component_classes never surfaces the base class itself."""
    classes = component_classes("docutils.transforms", Transform)
    assert Transform not in classes


def test_transform_fact_rows_with_priority_and_phase() -> None:
    """Fact rows surface priority and registration phase."""
    rows = _transform_fact_rows(
        TransformInfo(cls=_DemoTransform, registered_via="add_post_transform"),
    )
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Python path"].endswith("_DemoTransform")
    assert by_label["Default priority"] == "321"
    assert by_label["Registered via"] == "app.add_post_transform()"


def test_transform_fact_rows_without_priority() -> None:
    """A None default_priority renders as an em dash."""
    rows = _transform_fact_rows(TransformInfo(cls=_BareTransform))
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Default priority"] == "—"
    assert "Registered via" not in by_label


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------


def test_discover_readers_scans_module() -> None:
    """discover_readers finds reader subclasses defined in a module."""
    readers = discover_readers("docutils.readers.standalone")
    assert [cls.__name__ for cls in readers] == ["Reader"]


def test_discover_readers_empty_for_module_without_readers() -> None:
    """discover_readers returns [] for modules without readers."""
    assert discover_readers("sphinx_fonts") == []


def test_discover_reader_single_path() -> None:
    """discover_reader imports one reader from a dotted path."""
    cls = discover_reader("docutils.readers.standalone.Reader")
    assert cls.supported == ("standalone",)


def test_reader_fact_rows_surface_formats_and_transforms() -> None:
    """Reader fact rows include formats, config section, and transforms."""
    from docutils.readers.standalone import Reader

    rows = _reader_fact_rows(Reader)
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Python path"] == "docutils.readers.standalone.Reader"
    assert by_label["Supported formats"] == "standalone"
    assert by_label["Config section"] == "standalone reader"
    assert "Transitions" in by_label["Transforms"]


def test_reader_fact_rows_dash_for_empty_metadata() -> None:
    """Readers without formats or instantiable transforms degrade to dashes."""
    from docutils.readers import Reader as BaseReader

    class _OpaqueReader(BaseReader):  # type: ignore[type-arg]
        """Reader whose transform set cannot be resolved."""

        config_section = ""

        def get_transforms(self) -> list[type]:
            raise RuntimeError("needs framework state")

    rows = _reader_fact_rows(_OpaqueReader)
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Supported formats"] == "—"
    assert by_label["Config section"] == "—"
    assert by_label["Transforms"] == "—"


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def test_source_parsers_from_calls_filters_parser_classes() -> None:
    """_source_parsers_from_calls keeps only Parser subclasses."""
    from docutils.parsers.rst import Parser as RstParser

    classes = _source_parsers_from_calls(
        [
            ("add_source_parser", (RstParser,), {}),
            ("add_source_parser", (object,), {}),
            ("add_directive", ("noise", object), {}),
        ],
    )
    assert classes == [RstParser]


def test_discover_parsers_scans_module() -> None:
    """discover_parsers finds parser subclasses defined in a module."""
    infos = discover_parsers("docutils.parsers.rst")
    assert [(info.cls.__name__, info.registered_via) for info in infos] == [
        ("Parser", ""),
    ]


def test_discover_parsers_empty_for_module_without_parsers() -> None:
    """discover_parsers returns [] for modules without parsers."""
    assert discover_parsers("sphinx_fonts") == []


def test_discover_parser_single_path() -> None:
    """discover_parser imports one parser from a dotted path."""
    info = discover_parser("docutils.parsers.rst.Parser")
    assert "restructuredtext" in info.aliases


def test_parser_fact_rows_surface_aliases() -> None:
    """Parser fact rows include the alias tuple and config section."""
    from docutils.parsers.rst import Parser as RstParser

    rows = _parser_fact_rows(ParserInfo(cls=RstParser))
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Python path"] == "docutils.parsers.rst.Parser"
    assert "rst" in by_label["Supported aliases"]
    assert by_label["Config section"] == "restructuredtext parser"
    assert "Registered via" not in by_label


def test_parser_fact_rows_include_source_parser_registration() -> None:
    """A registered source parser surfaces its add_source_parser call."""
    from docutils.parsers.rst import Parser as RstParser

    rows = _parser_fact_rows(
        ParserInfo(cls=RstParser, registered_via="add_source_parser"),
    )
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Registered via"] == "app.add_source_parser()"


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


class _demo_inline(nodes.General, nodes.Inline, nodes.Element):  # noqa: N801 — docutils node classes are lowercase
    """Demo inline node for metadata tests."""


def _visit_demo_inline(translator: object, node: object) -> None:
    """Demo visit handler."""


def _depart_demo_inline(translator: object, node: object) -> None:
    """Demo depart handler."""


class NodesFromCallsCase(t.NamedTuple):
    """Test case for _nodes_from_calls()."""

    test_id: str
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]]
    expected: list[tuple[str, tuple[str, ...]]]


_NODES_FROM_CALLS_CASES: list[NodesFromCallsCase] = [
    NodesFromCallsCase(
        test_id="single_builder",
        calls=[
            (
                "add_node",
                (_demo_inline,),
                {"html": (_visit_demo_inline, _depart_demo_inline)},
            ),
        ],
        expected=[("_demo_inline", ("html",))],
    ),
    NodesFromCallsCase(
        test_id="override_kwarg_skipped",
        calls=[
            (
                "add_node",
                (_demo_inline,),
                {"override": True, "html": (_visit_demo_inline, None)},
            ),
        ],
        expected=[("_demo_inline", ("html",))],
    ),
    NodesFromCallsCase(
        test_id="multiple_builders",
        calls=[
            (
                "add_node",
                (_demo_inline,),
                {
                    "html": (_visit_demo_inline, None),
                    "latex": (_visit_demo_inline, None),
                },
            ),
        ],
        expected=[("_demo_inline", ("html", "latex"))],
    ),
    NodesFromCallsCase(
        test_id="last_registration_wins",
        calls=[
            ("add_node", (_demo_inline,), {"html": (_visit_demo_inline, None)}),
            ("add_node", (_demo_inline,), {"text": (_visit_demo_inline, None)}),
        ],
        expected=[("_demo_inline", ("text",))],
    ),
    NodesFromCallsCase(
        test_id="ignores_non_node_classes",
        calls=[("add_node", (object,), {})],
        expected=[],
    ),
]


@pytest.mark.parametrize(
    "case",
    _NODES_FROM_CALLS_CASES,
    ids=lambda c: c.test_id,
)
def test_nodes_from_calls(case: NodesFromCallsCase) -> None:
    """_nodes_from_calls extracts node registrations with handlers."""
    infos = _nodes_from_calls(case.calls)
    assert [(info.cls.__name__, info.handlers) for info in infos] == case.expected


def test_discover_nodes_merges_registration_into_scan() -> None:
    """discover_nodes surfaces registered nodes with their handlers."""
    infos = discover_nodes("sphinx_ux_badges")
    assert [(info.cls.__name__, info.handlers) for info in infos] == [
        ("BadgeNode", ("html",)),
    ]


def test_discover_nodes_empty_for_module_without_nodes() -> None:
    """discover_nodes returns [] for modules without node classes."""
    assert discover_nodes("sphinx_fonts") == []


def test_discover_node_single_path() -> None:
    """discover_node imports one node class and picks up its handlers."""
    info = discover_node("sphinx_ux_badges.BadgeNode")
    assert info.cls.__name__ == "BadgeNode"


def test_node_categories_for_inline_node() -> None:
    """node_categories reports docutils element category mixins.

    ``General`` subclasses ``Body`` in docutils, so a General node is
    also a Body node.
    """
    assert node_categories(_demo_inline) == ["Body", "General", "Inline"]


def test_node_fact_rows_surface_bases_and_handlers() -> None:
    """Node fact rows include base classes, categories, and handlers."""
    rows = _node_fact_rows(NodeInfo(cls=_demo_inline, handlers=("html",)))
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Python path"].endswith("_demo_inline")
    assert "General" in by_label["Base classes"]
    assert by_label["Categories"] == "Body, General, Inline"
    assert by_label["Visit/depart handlers"] == "html"


def test_node_fact_rows_dash_without_handlers() -> None:
    """Translator-handled nodes (no add_node call) show a handler dash."""
    rows = _node_fact_rows(NodeInfo(cls=_demo_inline))
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Visit/depart handlers"] == "—"


# ---------------------------------------------------------------------------
# Translators
# ---------------------------------------------------------------------------


class _DemoVisitor(nodes.SparseNodeVisitor):
    """Demo translator overriding two paragraph handlers."""

    def visit_paragraph(self, node: nodes.paragraph) -> None:
        """Demo visit handler."""

    def depart_paragraph(self, node: nodes.paragraph) -> None:
        """Demo depart handler."""


def test_translator_overrides_lists_own_methods_only() -> None:
    """translator_overrides reports only methods defined on the class."""
    assert translator_overrides(_DemoVisitor) == [
        "depart_paragraph",
        "visit_paragraph",
    ]


def test_translators_from_calls_extracts_builder_and_override() -> None:
    """_translators_from_calls captures builder name and override flag."""
    infos = _translators_from_calls(
        [
            ("set_translator", ("html", _DemoVisitor), {"override": True}),
            ("set_translator", ("text", _DemoVisitor, False), {}),
            ("set_translator", (123, _DemoVisitor), {}),
            ("add_directive", ("noise", object), {}),
        ],
    )
    assert [(info.builder_name, info.override) for info in infos] == [
        ("html", True),
        ("text", False),
    ]


def test_discover_translators_scans_module() -> None:
    """discover_translators finds NodeVisitor subclasses in a module."""
    infos = discover_translators("docutils.writers.html5_polyglot")
    assert [(info.cls.__name__, info.builder_name) for info in infos] == [
        ("HTMLTranslator", ""),
    ]


def test_discover_translators_empty_for_module_without_translators() -> None:
    """discover_translators returns [] for modules without translators."""
    assert discover_translators("sphinx_fonts") == []


def test_discover_translator_single_path() -> None:
    """discover_translator imports one translator from a dotted path."""
    info = discover_translator("docutils.writers.html5_polyglot.HTMLTranslator")
    assert info.cls.__name__ == "HTMLTranslator"


def test_translator_fact_rows_surface_base_and_overrides() -> None:
    """Translator fact rows include base class and own overrides."""
    rows = _translator_fact_rows(TranslatorInfo(cls=_DemoVisitor))
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Base class"] == "SparseNodeVisitor"
    assert by_label["Overrides"] == "depart_paragraph, visit_paragraph"
    assert "Registered for builder" not in by_label


def test_translator_fact_rows_include_builder_registration() -> None:
    """A set_translator registration surfaces the builder name."""
    rows = _translator_fact_rows(
        TranslatorInfo(cls=_DemoVisitor, builder_name="html", override=True),
    )
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Registered for builder"] == "html"


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def test_discover_writers_scans_module() -> None:
    """discover_writers finds writer subclasses defined in a module."""
    writers = discover_writers("docutils.writers.html5_polyglot")
    assert [cls.__name__ for cls in writers] == ["Writer"]


def test_discover_writers_empty_for_module_without_writers() -> None:
    """discover_writers returns [] for modules without writers."""
    assert discover_writers("sphinx_fonts") == []


def test_discover_writer_single_path() -> None:
    """discover_writer imports one writer from a dotted path."""
    cls = discover_writer("docutils.writers.html5_polyglot.Writer")
    assert "html5" in cls.supported


def test_resolve_translator_class_from_init_assignment() -> None:
    """Writers assigning translator_class in __init__ still resolve."""
    from docutils.writers import Writer as BaseWriter

    class _InitWriter(BaseWriter):  # type: ignore[type-arg]
        """Writer assigning its translator at construction time."""

        def __init__(self) -> None:
            super().__init__()
            self.translator_class = nodes.SparseNodeVisitor

        def translate(self) -> None:
            self.output = ""

    assert resolve_translator_class(_InitWriter) is nodes.SparseNodeVisitor


def test_resolve_translator_class_falls_back_to_class_attr() -> None:
    """Writers that raise on construction fall back to the class attribute."""
    from docutils.writers import Writer as BaseWriter

    class _FussyWriter(BaseWriter):  # type: ignore[type-arg]
        """Writer that needs framework state to construct."""

        translator_class = nodes.SparseNodeVisitor

        def __init__(self) -> None:
            raise RuntimeError("needs framework state")

        def translate(self) -> None:
            self.output = ""

    assert resolve_translator_class(_FussyWriter) is nodes.SparseNodeVisitor


def test_writer_fact_rows_surface_formats_and_translator() -> None:
    """Writer fact rows include formats, translator path, and transforms."""
    from docutils.writers import html5_polyglot

    rows = _writer_fact_rows(html5_polyglot.Writer)
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Python path"] == "docutils.writers.html5_polyglot.Writer"
    assert "html5" in by_label["Supported formats"]
    assert by_label["Translator class"] == (
        "docutils.writers.html5_polyglot.HTMLTranslator"
    )
    assert by_label["Transforms"] != ""


def test_registered_via_fact_links_sphinx_app() -> None:
    """The Registered via fact targets the Sphinx Application method."""
    rows = _transform_fact_rows(
        TransformInfo(cls=_DemoTransform, registered_via="add_transform"),
    )
    row = next(r for r in rows if r.label == "Registered via")
    xref = next(iter(row.body.findall(addnodes.pending_xref)))
    assert xref["reftarget"] == "sphinx.application.Sphinx.add_transform"
    assert xref.astext() == "app.add_transform()"


def test_option_field_list_links_converter() -> None:
    """Directive option validators link to their converter callable."""
    from docutils.parsers.rst import directives

    from sphinx_autodoc_docutils._directives import _option_field_list

    field_list = _option_field_list({"class": directives.class_option})
    assert field_list is not None
    xref = next(iter(field_list.findall(addnodes.pending_xref)))
    assert xref["reftarget"] == "docutils.parsers.rst.directives.class_option"
    assert xref.astext() == "class_option"
