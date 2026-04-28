"""Tests for :mod:`gp_sphinx_astro_builder.translator`.

These are pure tree-unit tests: build a docutils doctree directly, walk it
through the translator, and assert the result. No Sphinx app is constructed.
"""

from __future__ import annotations

import typing as t

import docutils.frontend
import docutils.parsers.rst
import docutils.utils
import pytest
from docutils import nodes

from gp_sphinx_astro_builder.models import (
    AdmonitionNode,
    BlockQuoteNode,
    BulletListNode,
    CommentNode,
    DefinitionListItemNode,
    DefinitionListNode,
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


def test_translator_handles_block_quote_with_paragraph() -> None:
    """A block_quote becomes a BlockQuoteNode wrapping its block children."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    block_quote = nodes.block_quote()
    quoted_para = nodes.paragraph()
    quoted_para += nodes.Text("Quoted text.")
    block_quote += quoted_para
    section += title
    section += block_quote
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    block_child = translator.result().tree.children[0]
    assert isinstance(block_child, BlockQuoteNode)
    assert isinstance(block_child.children[0], ParagraphNode)
    assert block_child.children[0].children == [
        TextNode(type="text", value="Quoted text."),
    ]


def _list_item_with(text: str) -> nodes.list_item:
    """Return a list_item containing a paragraph with ``text``."""
    item = nodes.list_item()
    para = nodes.paragraph()
    para += nodes.Text(text)
    item += para
    return item


def test_translator_handles_bullet_list() -> None:
    """A bullet_list with two items becomes BulletListNode + ListItemNode children."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    bl = nodes.bullet_list()
    bl += _list_item_with("apple")
    bl += _list_item_with("banana")
    section += title
    section += bl
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    list_child = translator.result().tree.children[0]
    assert isinstance(list_child, BulletListNode)
    assert len(list_child.children) == 2
    first_item = list_child.children[0]
    assert isinstance(first_item, ListItemNode)
    inner_paragraph = first_item.children[0]
    assert isinstance(inner_paragraph, ParagraphNode)
    assert inner_paragraph.children == [TextNode(type="text", value="apple")]


def test_translator_handles_enumerated_list_with_start() -> None:
    """An enumerated_list with start=3 becomes EnumeratedListNode with start=3."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    el = nodes.enumerated_list()
    el["start"] = 3
    el += _list_item_with("c")
    section += title
    section += el
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    list_child = translator.result().tree.children[0]
    assert isinstance(list_child, EnumeratedListNode)
    assert list_child.start == 3
    assert len(list_child.children) == 1


def test_translator_enumerated_list_without_start_is_none() -> None:
    """An enumerated_list without start attribute produces start=None."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    el = nodes.enumerated_list()
    el += _list_item_with("a")
    section += title
    section += el
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    list_child = translator.result().tree.children[0]
    assert isinstance(list_child, EnumeratedListNode)
    assert list_child.start is None


def test_translator_handles_nested_bullet_lists() -> None:
    """A bullet_list nested inside a list_item becomes nested BulletListNodes."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    outer = nodes.bullet_list()
    item = nodes.list_item()
    inner = nodes.bullet_list()
    inner += _list_item_with("inner")
    item += inner
    outer += item
    section += title
    section += outer
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    outer_list = translator.result().tree.children[0]
    assert isinstance(outer_list, BulletListNode)
    outer_item = outer_list.children[0]
    assert isinstance(outer_item, ListItemNode)
    inner_list = outer_item.children[0]
    assert isinstance(inner_list, BulletListNode)


class AdmonitionTranslatorFixture(t.NamedTuple):
    """Pairs a docutils admonition node class with its expected variant string."""

    test_id: str
    node_class: type[nodes.Element]
    variant: str


_ADMONITION_TRANSLATOR_FIXTURES: list[AdmonitionTranslatorFixture] = [
    AdmonitionTranslatorFixture("note", nodes.note, "note"),
    AdmonitionTranslatorFixture("warning", nodes.warning, "warning"),
    AdmonitionTranslatorFixture("attention", nodes.attention, "attention"),
    AdmonitionTranslatorFixture("caution", nodes.caution, "caution"),
    AdmonitionTranslatorFixture("important", nodes.important, "important"),
    AdmonitionTranslatorFixture("tip", nodes.tip, "tip"),
    AdmonitionTranslatorFixture("hint", nodes.hint, "hint"),
    AdmonitionTranslatorFixture("danger", nodes.danger, "danger"),
    AdmonitionTranslatorFixture("error", nodes.error, "error"),
]


@pytest.mark.parametrize(
    list(AdmonitionTranslatorFixture._fields),
    _ADMONITION_TRANSLATOR_FIXTURES,
    ids=[f.test_id for f in _ADMONITION_TRANSLATOR_FIXTURES],
)
def test_translator_handles_each_admonition_variant(
    test_id: str,
    node_class: type[nodes.Element],
    variant: str,
) -> None:
    """Every typed admonition node maps to the matching AdmonitionNode variant."""
    del test_id
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")
    admonition = node_class()
    para = nodes.paragraph()
    para += nodes.Text("body")
    admonition += para
    section += title
    section += admonition
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    block_child = translator.result().tree.children[0]
    assert isinstance(block_child, AdmonitionNode)
    assert block_child.variant == variant
    assert isinstance(block_child.children[0], ParagraphNode)
    assert block_child.children[0].children == [TextNode(type="text", value="body")]


def test_translator_handles_definition_list() -> None:
    """A definition_list with one item produces nested DefinitionList shape."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")

    dl = nodes.definition_list()
    dli = nodes.definition_list_item()
    term = nodes.term()
    term += nodes.Text("foo")
    defn = nodes.definition()
    defn_para = nodes.paragraph()
    defn_para += nodes.Text("describes foo")
    defn += defn_para
    dli += term
    dli += defn
    dl += dli

    section += title
    section += dl
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    list_child = translator.result().tree.children[0]
    assert isinstance(list_child, DefinitionListNode)
    assert len(list_child.children) == 1
    item = list_child.children[0]
    assert isinstance(item, DefinitionListItemNode)
    assert item.term == [TextNode(type="text", value="foo")]
    assert len(item.definition) == 1
    defn_paragraph = item.definition[0]
    assert isinstance(defn_paragraph, ParagraphNode)
    assert defn_paragraph.children == [
        TextNode(type="text", value="describes foo"),
    ]


def test_translator_handles_definition_list_with_emphasis_in_term() -> None:
    """The term slot accepts inline children like emphasis runs."""
    doc = _new_document()
    section = nodes.section(ids=["s"])
    title = nodes.title()
    title += nodes.Text("S")

    dl = nodes.definition_list()
    dli = nodes.definition_list_item()
    term = nodes.term()
    em = nodes.emphasis()
    em += nodes.Text("emphasized")
    term += em
    defn = nodes.definition()
    defn_para = nodes.paragraph()
    defn_para += nodes.Text("body")
    defn += defn_para
    dli += term
    dli += defn
    dl += dli

    section += title
    section += dl
    doc += section

    translator = DocTreeJSONTranslator(doc, docname="s")
    doc.walkabout(translator)
    list_child = translator.result().tree.children[0]
    assert isinstance(list_child, DefinitionListNode)
    item = list_child.children[0]
    term_first = item.term[0]
    assert isinstance(term_first, EmphasisNode)
    assert term_first.children == [TextNode(type="text", value="emphasized")]


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
