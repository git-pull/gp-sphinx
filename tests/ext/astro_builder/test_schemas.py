"""Tests for :mod:`gp_sphinx_astro_builder.schemas`."""

from __future__ import annotations

import typing as t

from gp_sphinx_astro_builder.models import Document
from gp_sphinx_astro_builder.schemas import export_doctree_schema

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
