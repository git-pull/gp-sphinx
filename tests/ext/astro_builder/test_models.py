"""Tests for :mod:`gp_sphinx_astro_builder.models`."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gp_sphinx_astro_builder.models import (
    BlockQuoteNode,
    BulletListNode,
    CommentNode,
    Document,
    EmphasisNode,
    EnumeratedListNode,
    ImageNode,
    ListItemNode,
    LiteralBlockNode,
    LiteralNode,
    ParagraphNode,
    ReferenceNode,
    SectionNode,
    StrongNode,
    TextNode,
    TransitionNode,
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


def test_strong_round_trips_with_text_children() -> None:
    """``StrongNode`` accepts inline children and preserves nesting."""
    node = StrongNode.model_validate(
        {
            "type": "strong",
            "children": [{"type": "text", "value": "bold"}],
        },
    )
    assert isinstance(node.children[0], TextNode)
    assert node.model_dump() == {
        "type": "strong",
        "children": [{"type": "text", "value": "bold"}],
    }


def test_strong_supports_emphasis_through_inline_union() -> None:
    """``StrongNode`` accepts an emphasis child via the inline discriminator."""
    node = StrongNode.model_validate(
        {
            "type": "strong",
            "children": [
                {
                    "type": "emphasis",
                    "children": [{"type": "text", "value": "loud"}],
                },
            ],
        },
    )
    assert isinstance(node.children[0], EmphasisNode)


def test_literal_round_trips_with_value() -> None:
    """``LiteralNode`` carries an inline literal text value."""
    node = LiteralNode(type="literal", value="x = 1")
    assert node.model_dump() == {"type": "literal", "value": "x = 1"}


def test_literal_validates_canonical_shape() -> None:
    """``LiteralNode.model_validate`` parses the canonical dict."""
    node = LiteralNode.model_validate({"type": "literal", "value": "foo"})
    assert node.value == "foo"


def test_reference_round_trips_with_href_and_children() -> None:
    """``ReferenceNode`` carries an href plus inline children."""
    node = ReferenceNode.model_validate(
        {
            "type": "reference",
            "href": "https://example.com",
            "children": [{"type": "text", "value": "Example"}],
        },
    )
    assert node.href == "https://example.com"
    assert node.children == [TextNode(type="text", value="Example")]


def test_reference_round_trips_with_internal_anchor() -> None:
    """``ReferenceNode`` accepts internal anchor hrefs (``#section-id``)."""
    node = ReferenceNode.model_validate(
        {
            "type": "reference",
            "href": "#intro",
            "children": [{"type": "text", "value": "Intro"}],
        },
    )
    assert node.href == "#intro"


def test_image_round_trips_with_uri_only() -> None:
    """``ImageNode`` accepts a uri without alt."""
    node = ImageNode(type="image", uri="/img/logo.svg", alt=None)
    assert node.model_dump() == {
        "type": "image",
        "uri": "/img/logo.svg",
        "alt": None,
    }


def test_image_round_trips_with_uri_and_alt() -> None:
    """``ImageNode`` carries both uri and alt text."""
    node = ImageNode.model_validate(
        {"type": "image", "uri": "/img/logo.svg", "alt": "Logo"},
    )
    assert node.alt == "Logo"


def test_image_alt_defaults_to_none() -> None:
    """``ImageNode.alt`` defaults to ``None`` when omitted from the input."""
    node = ImageNode.model_validate({"type": "image", "uri": "/x.png"})
    assert node.alt is None


def test_literal_block_round_trips_with_language() -> None:
    """``LiteralBlockNode`` carries language tag and raw code."""
    node = LiteralBlockNode(
        type="literalBlock",
        language="python",
        code="print('hi')",
    )
    assert node.model_dump() == {
        "type": "literalBlock",
        "language": "python",
        "code": "print('hi')",
    }


def test_literal_block_language_defaults_to_none() -> None:
    """``LiteralBlockNode.language`` defaults to ``None`` when omitted."""
    node = LiteralBlockNode.model_validate(
        {"type": "literalBlock", "code": "raw text"},
    )
    assert node.language is None
    assert node.code == "raw text"


def test_comment_round_trips_with_value() -> None:
    """``CommentNode`` carries the raw comment text."""
    node = CommentNode(type="comment", value="hidden note")
    assert node.model_dump() == {"type": "comment", "value": "hidden note"}


def test_transition_has_no_payload() -> None:
    """``TransitionNode`` is a payload-less marker."""
    node = TransitionNode(type="transition")
    assert node.model_dump() == {"type": "transition"}


def test_block_quote_round_trips_with_paragraph_child() -> None:
    """``BlockQuoteNode`` carries block-level children."""
    node = BlockQuoteNode.model_validate(
        {
            "type": "blockQuote",
            "children": [
                {
                    "type": "paragraph",
                    "children": [{"type": "text", "value": "quoted"}],
                },
            ],
        },
    )
    assert isinstance(node.children[0], ParagraphNode)


def _make_para_payload(text: str) -> dict[str, object]:
    """Return a paragraph dict containing a single text child."""
    return {"type": "paragraph", "children": [{"type": "text", "value": text}]}


def test_list_item_round_trips_with_paragraph_child() -> None:
    """``ListItemNode`` carries block children."""
    node = ListItemNode.model_validate(
        {"type": "listItem", "children": [_make_para_payload("a")]},
    )
    assert isinstance(node.children[0], ParagraphNode)


def test_list_item_rejects_inline_child() -> None:
    """``ListItemNode`` rejects an inline node where a block is expected."""
    with pytest.raises(ValidationError):
        ListItemNode.model_validate(
            {"type": "listItem", "children": [{"type": "text", "value": "x"}]},
        )


def test_bullet_list_round_trips_with_list_items() -> None:
    """``BulletListNode`` accepts only list_item children."""
    node = BulletListNode.model_validate(
        {
            "type": "bulletList",
            "children": [
                {"type": "listItem", "children": [_make_para_payload("a")]},
                {"type": "listItem", "children": [_make_para_payload("b")]},
            ],
        },
    )
    assert len(node.children) == 2
    assert isinstance(node.children[0], ListItemNode)


def test_bullet_list_rejects_non_list_item_child() -> None:
    """``BulletListNode`` rejects a non-list_item child."""
    with pytest.raises(ValidationError):
        BulletListNode.model_validate(
            {
                "type": "bulletList",
                "children": [_make_para_payload("oops")],
            },
        )


def test_enumerated_list_round_trips_with_start() -> None:
    """``EnumeratedListNode`` carries an optional start integer."""
    node = EnumeratedListNode.model_validate(
        {
            "type": "enumeratedList",
            "start": 3,
            "children": [
                {"type": "listItem", "children": [_make_para_payload("c")]},
            ],
        },
    )
    assert node.start == 3
    assert isinstance(node.children[0], ListItemNode)


def test_enumerated_list_start_defaults_to_none() -> None:
    """``EnumeratedListNode.start`` defaults to ``None`` when omitted."""
    node = EnumeratedListNode.model_validate(
        {
            "type": "enumeratedList",
            "children": [
                {"type": "listItem", "children": [_make_para_payload("a")]},
            ],
        },
    )
    assert node.start is None


def test_block_quote_rejects_inline_child() -> None:
    """``BlockQuoteNode`` rejects an inline node where a block is expected."""
    with pytest.raises(ValidationError):
        BlockQuoteNode.model_validate(
            {
                "type": "blockQuote",
                "children": [{"type": "text", "value": "not a block"}],
            },
        )


def test_section_accepts_block_level_block_nodes() -> None:
    """``SectionNode`` accepts literalBlock, comment, and transition children."""
    node = SectionNode.model_validate(
        {
            "type": "section",
            "id": "x",
            "title": [{"type": "text", "value": "X"}],
            "children": [
                {"type": "literalBlock", "language": "python", "code": "x = 1"},
                {"type": "comment", "value": "TODO"},
                {"type": "transition"},
            ],
        },
    )
    assert isinstance(node.children[0], LiteralBlockNode)
    assert isinstance(node.children[1], CommentNode)
    assert isinstance(node.children[2], TransitionNode)


def test_paragraph_round_trips_with_inline_union_children() -> None:
    """``ParagraphNode`` accepts text, emphasis, strong, and literal children."""
    node = ParagraphNode.model_validate(
        {
            "type": "paragraph",
            "children": [
                {"type": "text", "value": "Hello "},
                {
                    "type": "emphasis",
                    "children": [{"type": "text", "value": "world"}],
                },
                {"type": "text", "value": " — "},
                {
                    "type": "strong",
                    "children": [{"type": "text", "value": "important"}],
                },
                {"type": "text", "value": " "},
                {"type": "literal", "value": "code"},
                {"type": "text", "value": "."},
            ],
        },
    )
    assert len(node.children) == 7
    assert isinstance(node.children[0], TextNode)
    assert isinstance(node.children[1], EmphasisNode)
    assert isinstance(node.children[3], StrongNode)
    assert isinstance(node.children[5], LiteralNode)


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
