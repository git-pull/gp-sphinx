"""Tests for :mod:`gp_sphinx_astro_builder.models`."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gp_sphinx_astro_builder.models import (
    Document,
    EmphasisNode,
    ParagraphNode,
    SectionNode,
    TextNode,
)


def test_text_node_round_trips_through_model_dump() -> None:
    """``TextNode`` preserves type discriminator and value through ``model_dump``."""
    node = TextNode(type="text", value="hello")
    assert node.model_dump() == {"type": "text", "value": "hello"}


def test_text_node_validates_canonical_shape() -> None:
    """``TextNode.model_validate`` parses a dict with the canonical shape."""
    node = TextNode.model_validate({"type": "text", "value": "world"})
    assert node.value == "world"
    assert node.type == "text"


def test_text_node_rejects_wrong_type_discriminator() -> None:
    """``TextNode`` rejects a dict whose ``type`` is not the literal ``"text"``."""
    with pytest.raises(ValidationError):
        TextNode.model_validate({"type": "paragraph", "value": "x"})


def test_text_node_rejects_missing_value() -> None:
    """``TextNode`` rejects a dict missing the required ``value`` field."""
    with pytest.raises(ValidationError):
        TextNode.model_validate({"type": "text"})


def test_emphasis_round_trips_with_text_children() -> None:
    """``EmphasisNode`` accepts inline children and preserves nesting."""
    node = EmphasisNode.model_validate(
        {
            "type": "emphasis",
            "children": [{"type": "text", "value": "stressed"}],
        },
    )
    assert isinstance(node.children[0], TextNode)
    assert node.model_dump() == {
        "type": "emphasis",
        "children": [{"type": "text", "value": "stressed"}],
    }


def test_emphasis_supports_nested_emphasis() -> None:
    """``EmphasisNode`` accepts another ``EmphasisNode`` through the inline union."""
    node = EmphasisNode.model_validate(
        {
            "type": "emphasis",
            "children": [
                {
                    "type": "emphasis",
                    "children": [{"type": "text", "value": "very"}],
                },
            ],
        },
    )
    assert isinstance(node.children[0], EmphasisNode)


def test_paragraph_round_trips_with_inline_union_children() -> None:
    """``ParagraphNode`` accepts both text and emphasis through the inline union."""
    node = ParagraphNode.model_validate(
        {
            "type": "paragraph",
            "children": [
                {"type": "text", "value": "Hello "},
                {
                    "type": "emphasis",
                    "children": [{"type": "text", "value": "world"}],
                },
                {"type": "text", "value": "."},
            ],
        },
    )
    assert len(node.children) == 3
    assert isinstance(node.children[0], TextNode)
    assert isinstance(node.children[1], EmphasisNode)
    assert isinstance(node.children[2], TextNode)


def test_paragraph_rejects_block_node_in_inline_position() -> None:
    """``ParagraphNode`` rejects a block-level node where inline is expected."""
    with pytest.raises(ValidationError):
        ParagraphNode.model_validate(
            {
                "type": "paragraph",
                "children": [
                    {"type": "section", "id": "x", "title": [], "children": []},
                ],
            },
        )


def test_section_round_trips_with_block_children() -> None:
    """``SectionNode`` carries id, inline title, and block children."""
    node = SectionNode.model_validate(
        {
            "type": "section",
            "id": "intro",
            "title": [{"type": "text", "value": "Introduction"}],
            "children": [
                {
                    "type": "paragraph",
                    "children": [{"type": "text", "value": "Hello."}],
                },
            ],
        },
    )
    assert node.id == "intro"
    assert isinstance(node.children[0], ParagraphNode)


def test_section_rejects_inline_node_in_block_position() -> None:
    """``SectionNode`` rejects an inline node where a block is expected."""
    with pytest.raises(ValidationError):
        SectionNode.model_validate(
            {
                "type": "section",
                "id": "x",
                "title": [],
                "children": [{"type": "text", "value": "wrong"}],
            },
        )


def test_section_supports_nested_sections() -> None:
    """``SectionNode`` accepts another ``SectionNode`` as a block child."""
    node = SectionNode.model_validate(
        {
            "type": "section",
            "id": "outer",
            "title": [{"type": "text", "value": "Outer"}],
            "children": [
                {
                    "type": "section",
                    "id": "inner",
                    "title": [{"type": "text", "value": "Inner"}],
                    "children": [],
                },
            ],
        },
    )
    assert isinstance(node.children[0], SectionNode)


def test_document_round_trips_complete_tree() -> None:
    """``Document`` wraps a section tree with id and title metadata."""
    payload = {
        "id": "index",
        "title": "Hello world",
        "tree": {
            "type": "section",
            "id": "hello-world",
            "title": [{"type": "text", "value": "Hello world"}],
            "children": [
                {
                    "type": "paragraph",
                    "children": [{"type": "text", "value": "Hello world."}],
                },
            ],
        },
    }
    doc = Document.model_validate(payload)
    assert doc.model_dump() == payload
