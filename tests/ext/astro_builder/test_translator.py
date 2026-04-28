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
    Document,
    EmphasisNode,
    LiteralNode,
    ParagraphNode,
    SectionNode,
    StrongNode,
    TextNode,
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
