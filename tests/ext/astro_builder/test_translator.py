"""Tests for :mod:`gp_sphinx_astro_builder.translator`.

These are pure tree-unit tests: build a docutils doctree directly, walk it
through the translator, and assert the result. No Sphinx app is constructed.
"""

from __future__ import annotations

import docutils.frontend
import docutils.parsers.rst
import docutils.utils
from docutils import nodes

from gp_sphinx_astro_builder.models import (
    CommentNode,
    Document,
    EmphasisNode,
    ImageNode,
    LiteralBlockNode,
    LiteralNode,
    ParagraphNode,
    ReferenceNode,
    SectionNode,
    StrongNode,
    TextNode,
    TransitionNode,
)
from gp_sphinx_astro_builder.translator import DocTreeJSONTranslator


def _new_document() -> nodes.document:
    """Return a minimal docutils document for tree-unit assembly."""
    settings = docutils.frontend.OptionParser(
        components=(docutils.parsers.rst.Parser,),
    ).get_default_values()
    return docutils.utils.new_document("<test>", settings)


def test_translator_emits_document_for_one_paragraph() -> None:
    """A section with a title and one paragraph round-trips through the translator."""
    doc = _new_document()
    section = nodes.section(ids=["hello-world"])
    title = nodes.title()
    title += nodes.Text("Hello world")
    para = nodes.paragraph()
    para += nodes.Text("Hello world.")
    section += title
    section += para
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="index")
    doc.walkabout(translator)
    result = translator.result()

    assert isinstance(result, Document)
    assert result.id == "index"
    assert result.title == "Hello world"
    assert isinstance(result.tree, SectionNode)
    assert result.tree.id == "hello-world"
    assert result.tree.title == [TextNode(type="text", value="Hello world")]
    assert len(result.tree.children) == 1
    paragraph_child = result.tree.children[0]
    assert isinstance(paragraph_child, ParagraphNode)
    assert paragraph_child.children == [TextNode(type="text", value="Hello world.")]


def test_translator_handles_emphasis_inside_paragraph() -> None:
    """An emphasis run inside a paragraph becomes an EmphasisNode child."""
    doc = _new_document()
    section = nodes.section(ids=["intro"])
    title = nodes.title()
    title += nodes.Text("Intro")
    para = nodes.paragraph()
    para += nodes.Text("hello ")
    em = nodes.emphasis()
    em += nodes.Text("world")
    para += em
    section += title
    section += para
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="intro")
    doc.walkabout(translator)
    result = translator.result()

    paragraph_child = result.tree.children[0]
    assert isinstance(paragraph_child, ParagraphNode)
    assert len(paragraph_child.children) == 2
    assert paragraph_child.children[0] == TextNode(type="text", value="hello ")
    emphasis_child = paragraph_child.children[1]
    assert isinstance(emphasis_child, EmphasisNode)
    assert emphasis_child.children == [TextNode(type="text", value="world")]


def test_translator_handles_strong_inside_paragraph() -> None:
    """A strong run inside a paragraph becomes a StrongNode child."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    para = nodes.paragraph()
    strong = nodes.strong()
    strong += nodes.Text("loud")
    para += strong
    section += title
    section += para
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    paragraph_child = translator.result().tree.children[0]
    assert isinstance(paragraph_child, ParagraphNode)
    assert isinstance(paragraph_child.children[0], StrongNode)
    assert paragraph_child.children[0].children == [
        TextNode(type="text", value="loud"),
    ]


def test_translator_handles_literal_value() -> None:
    """A literal node captures text as a value field, not children."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    para = nodes.paragraph()
    literal = nodes.literal()
    literal += nodes.Text("x = 1")
    para += literal
    section += title
    section += para
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    paragraph_child = translator.result().tree.children[0]
    assert isinstance(paragraph_child, ParagraphNode)
    literal_child = paragraph_child.children[0]
    assert isinstance(literal_child, LiteralNode)
    assert literal_child.value == "x = 1"


def test_translator_handles_external_reference() -> None:
    """A reference with refuri becomes a ReferenceNode with that href."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    para = nodes.paragraph()
    ref = nodes.reference(refuri="https://example.com")
    ref += nodes.Text("Example")
    para += ref
    section += title
    section += para
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    paragraph_child = translator.result().tree.children[0]
    assert isinstance(paragraph_child, ParagraphNode)
    ref_child = paragraph_child.children[0]
    assert isinstance(ref_child, ReferenceNode)
    assert ref_child.href == "https://example.com"
    assert ref_child.children == [TextNode(type="text", value="Example")]


def test_translator_handles_internal_reference_via_refid() -> None:
    """A reference with refid becomes a ReferenceNode with a #anchor href."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    para = nodes.paragraph()
    ref = nodes.reference(refid="intro")
    ref += nodes.Text("see")
    para += ref
    section += title
    section += para
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    paragraph_child = translator.result().tree.children[0]
    assert isinstance(paragraph_child, ParagraphNode)
    ref_child = paragraph_child.children[0]
    assert isinstance(ref_child, ReferenceNode)
    assert ref_child.href == "#intro"


def test_translator_handles_image_with_uri_and_alt() -> None:
    """An image node becomes an ImageNode with uri and optional alt."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    para = nodes.paragraph()
    img = nodes.image(uri="/img/x.svg", alt="X")
    para += img
    section += title
    section += para
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    paragraph_child = translator.result().tree.children[0]
    assert isinstance(paragraph_child, ParagraphNode)
    img_child = paragraph_child.children[0]
    assert isinstance(img_child, ImageNode)
    assert img_child.uri == "/img/x.svg"
    assert img_child.alt == "X"


def test_translator_handles_image_without_alt() -> None:
    """An image node without alt produces ImageNode with alt=None."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    para = nodes.paragraph()
    img = nodes.image(uri="/img/x.svg")
    para += img
    section += title
    section += para
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    paragraph_child = translator.result().tree.children[0]
    assert isinstance(paragraph_child, ParagraphNode)
    img_child = paragraph_child.children[0]
    assert isinstance(img_child, ImageNode)
    assert img_child.alt is None


def test_translator_handles_literal_block_with_language() -> None:
    """A literal_block becomes a LiteralBlockNode with language and code."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    code_text = "print('hi')"
    block = nodes.literal_block(code_text, code_text)
    block["language"] = "python"
    section += title
    section += block
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    block_child = translator.result().tree.children[0]
    assert isinstance(block_child, LiteralBlockNode)
    assert block_child.language == "python"
    assert block_child.code == code_text


def test_translator_literal_block_without_language_is_none() -> None:
    """A literal_block without language attribute produces language=None."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    block = nodes.literal_block("raw", "raw")
    section += title
    section += block
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    block_child = translator.result().tree.children[0]
    assert isinstance(block_child, LiteralBlockNode)
    assert block_child.language is None
    assert block_child.code == "raw"


def test_translator_handles_comment_node() -> None:
    """A comment node becomes a CommentNode preserving the raw text."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    comment = nodes.comment("TODO write more", "TODO write more")
    section += title
    section += comment
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    comment_child = translator.result().tree.children[0]
    assert isinstance(comment_child, CommentNode)
    assert comment_child.value == "TODO write more"


def test_translator_handles_transition_node() -> None:
    """A transition node becomes a payload-less TransitionNode."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    section += title
    section += nodes.transition()
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    transition_child = translator.result().tree.children[0]
    assert isinstance(transition_child, TransitionNode)


def test_translator_handles_nested_sections() -> None:
    """A section nested inside another section becomes a block child."""
    doc = _new_document()
    outer = nodes.section(ids=["outer"])
    outer_title = nodes.title()
    outer_title += nodes.Text("Outer")
    inner = nodes.section(ids=["inner"])
    inner_title = nodes.title()
    inner_title += nodes.Text("Inner")
    inner += inner_title
    outer += outer_title
    outer += inner
    doc += outer

    translator = DocTreeJSONTranslator(doc, docname="nested")
    doc.walkabout(translator)
    result = translator.result()

    assert result.tree.id == "outer"
    assert len(result.tree.children) == 1
    nested_child = result.tree.children[0]
    assert isinstance(nested_child, SectionNode)
    assert nested_child.id == "inner"
    assert nested_child.title == [TextNode(type="text", value="Inner")]


def test_translator_result_validates_through_pydantic() -> None:
    """The translator result is a real Pydantic ``Document``, not a dict."""
    doc = _new_document()
    section = nodes.section(ids=["x"])
    title = nodes.title()
    title += nodes.Text("X")
    section += title
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="x")
    doc.walkabout(translator)
    result = translator.result()

    dumped = result.model_dump()
    revalidated = Document.model_validate(dumped)
    assert revalidated == result
