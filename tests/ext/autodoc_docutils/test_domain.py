"""Unit tests for DocutilsDomain.

Constructs DocutilsDomain against a lightweight stub env and exercises
the note / clear / merge / resolve lifecycle plus the grouped component
index. Cross-reference resolution against a real Sphinx build lives in
``test_domain_xref_integration.py``.
"""

from __future__ import annotations

import typing as t

import pytest

from sphinx_autodoc_docutils.domain import (
    NODE,
    OBJECT_TYPES,
    PARSER,
    READER,
    TRANSFORM,
    TRANSLATOR,
    WRITER,
    DocutilsComponentIndex,
    DocutilsDomain,
    split_component_path,
)


class _StubEnv:
    """Minimal stand-in for ``BuildEnvironment`` — just ``domaindata``."""

    def __init__(self) -> None:
        self.domaindata: dict[str, dict[str, t.Any]] = {}


def _make_domain() -> DocutilsDomain:
    """Build a DocutilsDomain bound to a fresh stub environment."""
    return DocutilsDomain(t.cast("t.Any", _StubEnv()))


def test_object_types_constants_match_domain() -> None:
    """Module-level objtype names match the domain's registered keys."""
    assert set(OBJECT_TYPES) == {
        TRANSFORM,
        READER,
        PARSER,
        WRITER,
        NODE,
        TRANSLATOR,
    }
    assert set(DocutilsDomain.object_types) == set(OBJECT_TYPES)
    assert set(DocutilsDomain.roles) == set(OBJECT_TYPES)
    assert set(DocutilsDomain.directives) == set(OBJECT_TYPES)


def test_initial_data_contains_empty_tables() -> None:
    """Fresh domain starts with one empty table per object type."""
    domain = _make_domain()
    for objtype in OBJECT_TYPES:
        assert domain.components(objtype) == {}


class SplitPathCase(t.NamedTuple):
    """Test case for split_component_path()."""

    test_id: str
    path: str
    expected_module: str
    expected_class: str


_SPLIT_PATH_CASES: list[SplitPathCase] = [
    SplitPathCase(
        test_id="dotted_path",
        path="pkg.transforms.SanitizeTransform",
        expected_module="pkg.transforms",
        expected_class="SanitizeTransform",
    ),
    SplitPathCase(
        test_id="single_segment",
        path="icon",
        expected_module="",
        expected_class="icon",
    ),
    SplitPathCase(
        test_id="deeply_nested",
        path="a.b.c.d.Writer",
        expected_module="a.b.c.d",
        expected_class="Writer",
    ),
]


@pytest.mark.parametrize(
    "case",
    _SPLIT_PATH_CASES,
    ids=lambda c: c.test_id,
)
def test_split_component_path(case: SplitPathCase) -> None:
    """split_component_path divides on the final dot."""
    assert split_component_path(case.path) == (
        case.expected_module,
        case.expected_class,
    )


class NoteComponentCase(t.NamedTuple):
    """Test case for DocutilsDomain.note_component() per objtype."""

    test_id: str
    objtype: str
    name: str
    docname: str
    anchor: str


_NOTE_COMPONENT_CASES: list[NoteComponentCase] = [
    NoteComponentCase(
        test_id="transform",
        objtype=TRANSFORM,
        name="pkg.transforms.SanitizeTransform",
        docname="api",
        anchor="docutils-transform-pkg-transforms-sanitizetransform",
    ),
    NoteComponentCase(
        test_id="reader",
        objtype=READER,
        name="pkg.readers.DemoReader",
        docname="api",
        anchor="docutils-reader-pkg-readers-demoreader",
    ),
    NoteComponentCase(
        test_id="parser",
        objtype=PARSER,
        name="pkg.parsers.DemoParser",
        docname="api",
        anchor="docutils-parser-pkg-parsers-demoparser",
    ),
    NoteComponentCase(
        test_id="writer",
        objtype=WRITER,
        name="pkg.writers.DemoWriter",
        docname="api",
        anchor="docutils-writer-pkg-writers-demowriter",
    ),
    NoteComponentCase(
        test_id="node",
        objtype=NODE,
        name="pkg.nodes.icon",
        docname="api",
        anchor="docutils-node-pkg-nodes-icon",
    ),
    NoteComponentCase(
        test_id="translator",
        objtype=TRANSLATOR,
        name="pkg.writers.DemoTranslator",
        docname="api",
        anchor="docutils-translator-pkg-writers-demotranslator",
    ),
]


@pytest.mark.parametrize(
    "case",
    _NOTE_COMPONENT_CASES,
    ids=lambda c: c.test_id,
)
def test_note_component_records_docname_and_anchor(case: NoteComponentCase) -> None:
    """note_component stores (docname, anchor) under the qualified name."""
    domain = _make_domain()
    domain.note_component(case.objtype, case.name, case.docname, case.anchor)
    assert domain.components(case.objtype) == {
        case.name: (case.docname, case.anchor),
    }
    for other in OBJECT_TYPES:
        if other != case.objtype:
            assert domain.components(other) == {}


def test_clear_doc_removes_only_matching_docname() -> None:
    """clear_doc drops entries from *docname* and keeps the rest."""
    domain = _make_domain()
    domain.note_component(TRANSFORM, "pkg.A", "page-a", "anchor-a")
    domain.note_component(TRANSFORM, "pkg.B", "page-b", "anchor-b")
    domain.note_component(WRITER, "pkg.W", "page-a", "anchor-w")

    domain.clear_doc("page-a")

    assert domain.components(TRANSFORM) == {"pkg.B": ("page-b", "anchor-b")}
    assert domain.components(WRITER) == {}


def test_merge_domaindata_merges_entries_within_docnames() -> None:
    """Parallel-worker merge retains entries for docnames in the active set."""
    domain = _make_domain()
    other: dict[str, t.Any] = {
        TRANSFORM: {"pkg.Sibling": ("pageB", "anchor-sibling")},
        NODE: {"pkg.icon": ("pageB", "anchor-icon")},
    }
    domain.merge_domaindata({"pageB"}, other)
    assert domain.components(TRANSFORM) == {"pkg.Sibling": ("pageB", "anchor-sibling")}
    assert domain.components(NODE) == {"pkg.icon": ("pageB", "anchor-icon")}


def test_merge_domaindata_ignores_entries_outside_docnames() -> None:
    """Entries whose docname is NOT in *docnames* are dropped on merge."""
    domain = _make_domain()
    other: dict[str, t.Any] = {
        TRANSFORM: {"pkg.Sibling": ("pageC", "anchor-sibling")},
    }
    domain.merge_domaindata({"pageB"}, other)
    assert domain.components(TRANSFORM) == {}


def test_get_objects_yields_every_registered_item() -> None:
    """get_objects iterates all six component tables."""
    domain = _make_domain()
    for objtype in OBJECT_TYPES:
        domain.note_component(
            objtype,
            f"pkg.{objtype.title()}",
            "api",
            f"docutils-{objtype}-anchor",
        )

    rows = list(domain.get_objects())
    assert {row[2] for row in rows} == set(OBJECT_TYPES)
    assert len(rows) == len(OBJECT_TYPES)


def test_lookup_exact_qualified_name() -> None:
    """_lookup resolves a fully-qualified component path."""
    domain = _make_domain()
    domain.note_component(TRANSFORM, "pkg.transforms.Sanitize", "api", "anchor")
    assert domain._lookup(TRANSFORM, "pkg.transforms.Sanitize") == ("api", "anchor")


def test_lookup_bare_class_name_when_unambiguous() -> None:
    """_lookup falls back to a unique bare class-name suffix match."""
    domain = _make_domain()
    domain.note_component(TRANSFORM, "pkg.transforms.Sanitize", "api", "anchor")
    assert domain._lookup(TRANSFORM, "Sanitize") == ("api", "anchor")


def test_lookup_bare_class_name_ambiguous_returns_none() -> None:
    """_lookup refuses an ambiguous bare class-name match."""
    domain = _make_domain()
    domain.note_component(TRANSFORM, "pkg_a.Sanitize", "api", "anchor-a")
    domain.note_component(TRANSFORM, "pkg_b.Sanitize", "api", "anchor-b")
    assert domain._lookup(TRANSFORM, "Sanitize") is None


def test_lookup_miss_returns_none() -> None:
    """_lookup returns None for unknown targets and unknown objtypes."""
    domain = _make_domain()
    assert domain._lookup(TRANSFORM, "pkg.Missing") is None
    assert domain._lookup("not-an-objtype", "pkg.Missing") is None


def test_component_index_groups_by_objtype() -> None:
    """The component index groups entries under per-objtype headings."""
    domain = _make_domain()
    domain.note_component(TRANSFORM, "pkg.B", "api", "anchor-b")
    domain.note_component(TRANSFORM, "pkg.A", "api", "anchor-a")
    domain.note_component(WRITER, "pkg.W", "api", "anchor-w")

    index = DocutilsComponentIndex(domain)
    content, collapse = index.generate()

    headings = [heading for heading, _entries in content]
    assert headings == ["Transforms", "Writers"]
    transform_entries = dict(content)["Transforms"]
    assert [entry.name for entry in transform_entries] == ["pkg.A", "pkg.B"]
    assert collapse is True


def test_component_index_filters_by_docnames() -> None:
    """The component index honours the *docnames* filter."""
    domain = _make_domain()
    domain.note_component(TRANSFORM, "pkg.A", "page-a", "anchor-a")
    domain.note_component(TRANSFORM, "pkg.B", "page-b", "anchor-b")

    index = DocutilsComponentIndex(domain)
    content, _collapse = index.generate(docnames=["page-b"])

    assert dict(content)["Transforms"][0].name == "pkg.B"
    assert len(dict(content)["Transforms"]) == 1
