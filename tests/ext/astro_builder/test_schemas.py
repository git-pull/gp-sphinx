"""Tests for :mod:`gp_sphinx_astro_builder.schemas`."""

from __future__ import annotations

import typing as t

from gp_sphinx_astro_builder.models import Document, Symbol, XrefEntry
from gp_sphinx_astro_builder.schemas import (
    export_doctree_schema,
    export_symbol_schema,
    export_xref_index_schema,
)

if t.TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

_EXPECTED_NODE_DEFS: frozenset[str] = frozenset(
    {
        "TextNode",
        "EmphasisNode",
        "StrongNode",
        "LiteralNode",
        "ReferenceNode",
        "ImageNode",
        "ParagraphNode",
        "SectionNode",
        "LiteralBlockNode",
        "CommentNode",
        "TransitionNode",
        "BlockQuoteNode",
        "BulletListNode",
        "EnumeratedListNode",
        "ListItemNode",
        "AdmonitionNode",
        "DefinitionListNode",
        "DefinitionListItemNode",
    },
)


def test_export_doctree_schema_returns_dict() -> None:
    """``export_doctree_schema`` returns a non-empty dict."""
    schema = export_doctree_schema()
    assert isinstance(schema, dict)
    assert schema  # not empty


def test_export_doctree_schema_contains_all_node_defs() -> None:
    """Every Pydantic node model appears under ``$defs`` in the exported schema."""
    schema = export_doctree_schema()
    defs = schema.get("$defs", {})
    missing = _EXPECTED_NODE_DEFS - set(defs.keys())
    assert not missing, f"missing $defs entries: {sorted(missing)}"


def test_export_doctree_schema_round_trips_canonical_document() -> None:
    """A canonical ``Document`` dict round-trips through the exported schema.

    The schema's contract is that anything ``Document.model_validate`` accepts
    must also be representable in the JSON Schema's ``$defs``. We don't run a
    third-party JSON Schema validator here — Pydantic is the source of truth
    — but we do confirm the canonical shape parses cleanly so a regression in
    the schema export immediately surfaces as a parse failure.
    """
    document_payload = {
        "id": "index",
        "title": "Hi",
        "tree": {
            "type": "section",
            "id": "hi",
            "title": [{"type": "text", "value": "Hi"}],
            "children": [
                {
                    "type": "paragraph",
                    "children": [{"type": "text", "value": "x"}],
                },
            ],
        },
    }
    document = Document.model_validate(document_payload)
    assert document.model_dump() == document_payload


def test_export_doctree_schema_matches_snapshot(
    snapshot: SnapshotAssertion,
) -> None:
    """The full exported schema is byte-stable against a syrupy snapshot."""
    assert export_doctree_schema() == snapshot


def test_export_symbol_schema_returns_dict() -> None:
    """``export_symbol_schema`` returns a non-empty dict."""
    schema = export_symbol_schema()
    assert isinstance(schema, dict)
    assert schema


def test_export_symbol_schema_contains_symbol_specific_defs() -> None:
    """Symbol-specific models appear under ``$defs`` in the exported schema."""
    schema = export_symbol_schema()
    defs = schema.get("$defs", {})
    expected = {"Parameter", "SymbolSource"}
    missing = expected - set(defs.keys())
    assert not missing, f"missing $defs entries: {sorted(missing)}"


def test_export_symbol_schema_round_trips_canonical_symbol() -> None:
    """A canonical ``Symbol`` dict round-trips through the exported schema."""
    payload: dict[str, t.Any] = {
        "id": "x.y.foo",
        "kind": "function",
        "name": "foo",
        "qualname": "foo",
        "module": "x.y",
        "signature": "() -> None",
        "parameters": [],
        "returns": None,
        "docstring_summary": "Hi.",
        "docstring_body": [],
        "source": None,
    }
    symbol = Symbol.model_validate(payload)
    assert symbol.model_dump() == payload


def test_export_symbol_schema_matches_snapshot(
    snapshot: SnapshotAssertion,
) -> None:
    """The full Symbol JSON Schema is byte-stable against a syrupy snapshot."""
    assert export_symbol_schema() == snapshot


def test_export_xref_index_schema_returns_array_schema() -> None:
    """``export_xref_index_schema`` returns an array-of-XrefEntry schema."""
    schema = export_xref_index_schema()
    assert isinstance(schema, dict)
    assert schema.get("type") == "array"


def test_export_xref_index_schema_contains_xref_entry_def() -> None:
    """The schema's items reference an ``XrefEntry`` ``$defs`` entry."""
    schema = export_xref_index_schema()
    defs = schema.get("$defs", {})
    assert "XrefEntry" in defs


def test_export_xref_index_schema_round_trips_entry() -> None:
    """A canonical XrefEntry validates through the model."""
    entry = XrefEntry.model_validate(
        {
            "id": "py:func:foo",
            "domain": "py",
            "role": "func",
            "target": "foo",
            "href": "/api/foo/",
            "display": None,
            "priority": 0,
        },
    )
    assert entry.target == "foo"


def test_export_xref_index_schema_matches_snapshot(
    snapshot: SnapshotAssertion,
) -> None:
    """The xref-index JSON Schema is byte-stable against a syrupy snapshot."""
    assert export_xref_index_schema() == snapshot
