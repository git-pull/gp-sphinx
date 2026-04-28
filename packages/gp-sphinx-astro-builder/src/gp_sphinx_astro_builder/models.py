"""Pydantic models for the doctree-as-typed-JSON wire format.

Each docutils node type the builder emits has a matching Pydantic model. The
``type`` discriminator lets every node validate as part of a discriminated
union without ambiguity, and lets the TypeScript side dispatch on the same
field at render time.
"""

from __future__ import annotations

import typing as t

from pydantic import BaseModel, Field


class TextNode(BaseModel):
    """A leaf node containing literal text.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import TextNode
    >>> node = TextNode(type="text", value="hello")
    >>> node.model_dump()
    {'type': 'text', 'value': 'hello'}
    """

    type: t.Literal["text"]
    value: str


class EmphasisNode(BaseModel):
    """An inline emphasis node wrapping inline children.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import EmphasisNode
    >>> node = EmphasisNode.model_validate(
    ...     {"type": "emphasis", "children": [{"type": "text", "value": "x"}]},
    ... )
    >>> node.children[0].value
    'x'
    """

    type: t.Literal["emphasis"]
    children: list[InlineNode]


class StrongNode(BaseModel):
    """An inline strong-emphasis node wrapping inline children.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import StrongNode
    >>> node = StrongNode.model_validate(
    ...     {"type": "strong", "children": [{"type": "text", "value": "x"}]},
    ... )
    >>> node.children[0].value
    'x'
    """

    type: t.Literal["strong"]
    children: list[InlineNode]


class LiteralNode(BaseModel):
    """An inline literal-text run, e.g. an inline code span.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import LiteralNode
    >>> LiteralNode(type="literal", value="x = 1").value
    'x = 1'
    """

    type: t.Literal["literal"]
    value: str


class ReferenceNode(BaseModel):
    """An inline cross-reference or external link.

    The ``href`` field holds either an absolute URL (when the source had
    ``refuri``) or an in-page anchor like ``"#section-id"`` (when the source
    had ``refid``). The translator normalises both into the same field so the
    Astro renderer needs a single href branch.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import ReferenceNode
    >>> node = ReferenceNode.model_validate(
    ...     {
    ...         "type": "reference",
    ...         "href": "https://example.com",
    ...         "children": [{"type": "text", "value": "Example"}],
    ...     },
    ... )
    >>> node.href
    'https://example.com'
    """

    type: t.Literal["reference"]
    href: str
    children: list[InlineNode]


class ImageNode(BaseModel):
    """An inline image leaf with a uri and optional alt text.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import ImageNode
    >>> ImageNode(type="image", uri="/img/x.svg", alt="X").alt
    'X'
    """

    type: t.Literal["image"]
    uri: str
    alt: str | None = None


class LiteralBlockNode(BaseModel):
    """A block-level fenced code block.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import LiteralBlockNode
    >>> node = LiteralBlockNode(type="literalBlock", language="py", code="x")
    >>> node.language
    'py'
    """

    type: t.Literal["literalBlock"]
    language: str | None = None
    code: str


class CommentNode(BaseModel):
    """A docutils comment block, preserved as raw text.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import CommentNode
    >>> CommentNode(type="comment", value="TODO").value
    'TODO'
    """

    type: t.Literal["comment"]
    value: str


class TransitionNode(BaseModel):
    """A transition (horizontal rule) marker with no payload.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import TransitionNode
    >>> TransitionNode(type="transition").type
    'transition'
    """

    type: t.Literal["transition"]


class BlockQuoteNode(BaseModel):
    """A block-level quote wrapping block-level children.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import BlockQuoteNode
    >>> node = BlockQuoteNode.model_validate(
    ...     {
    ...         "type": "blockQuote",
    ...         "children": [
    ...             {
    ...                 "type": "paragraph",
    ...                 "children": [{"type": "text", "value": "q"}],
    ...             },
    ...         ],
    ...     },
    ... )
    >>> node.children[0].children[0].value
    'q'
    """

    type: t.Literal["blockQuote"]
    children: list[BlockNode]


class ListItemNode(BaseModel):
    """One item in a bullet or enumerated list.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import ListItemNode
    >>> node = ListItemNode.model_validate(
    ...     {
    ...         "type": "listItem",
    ...         "children": [
    ...             {
    ...                 "type": "paragraph",
    ...                 "children": [{"type": "text", "value": "a"}],
    ...             },
    ...         ],
    ...     },
    ... )
    >>> node.children[0].children[0].value
    'a'
    """

    type: t.Literal["listItem"]
    children: list[BlockNode]


class BulletListNode(BaseModel):
    """A bullet (unordered) list whose children are list items.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import BulletListNode
    >>> node = BulletListNode.model_validate(
    ...     {"type": "bulletList", "children": []},
    ... )
    >>> node.children
    []
    """

    type: t.Literal["bulletList"]
    children: list[ListItemNode]


class EnumeratedListNode(BaseModel):
    """An enumerated (ordered) list with optional explicit ``start`` index.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import EnumeratedListNode
    >>> node = EnumeratedListNode.model_validate(
    ...     {"type": "enumeratedList", "children": []},
    ... )
    >>> node.start is None
    True
    """

    type: t.Literal["enumeratedList"]
    start: int | None = None
    children: list[ListItemNode]


AdmonitionVariant = t.Literal[
    "note",
    "warning",
    "attention",
    "caution",
    "important",
    "tip",
    "hint",
    "danger",
    "error",
]
"""Allowed values for :attr:`AdmonitionNode.variant`.

The nine variants correspond one-to-one with docutils' typed admonition node
classes (``nodes.note``, ``nodes.warning``, etc.); the translator collapses
them into a single Pydantic model so the Astro renderer dispatches on one
component instead of nine.
"""


class AdmonitionNode(BaseModel):
    """A block-level admonition (note, warning, tip, …).

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import AdmonitionNode
    >>> node = AdmonitionNode.model_validate(
    ...     {
    ...         "type": "admonition",
    ...         "variant": "note",
    ...         "children": [
    ...             {
    ...                 "type": "paragraph",
    ...                 "children": [{"type": "text", "value": "x"}],
    ...             },
    ...         ],
    ...     },
    ... )
    >>> node.variant
    'note'
    """

    type: t.Literal["admonition"]
    variant: AdmonitionVariant
    children: list[BlockNode]


class ParagraphNode(BaseModel):
    """A block-level paragraph wrapping inline children.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import ParagraphNode
    >>> node = ParagraphNode.model_validate(
    ...     {"type": "paragraph", "children": [{"type": "text", "value": "hi"}]},
    ... )
    >>> node.children[0].value
    'hi'
    """

    type: t.Literal["paragraph"]
    children: list[InlineNode]


class SectionNode(BaseModel):
    """A document section with id, inline title, and block children.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import SectionNode
    >>> node = SectionNode.model_validate(
    ...     {
    ...         "type": "section",
    ...         "id": "intro",
    ...         "title": [{"type": "text", "value": "Intro"}],
    ...         "children": [],
    ...     },
    ... )
    >>> node.id
    'intro'
    """

    type: t.Literal["section"]
    id: str
    title: list[InlineNode]
    children: list[BlockNode]


class Document(BaseModel):
    """The top-level wrapper for one source document.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import Document
    >>> doc = Document.model_validate(
    ...     {
    ...         "id": "index",
    ...         "title": "Hi",
    ...         "tree": {
    ...             "type": "section",
    ...             "id": "hi",
    ...             "title": [{"type": "text", "value": "Hi"}],
    ...             "children": [],
    ...         },
    ...     },
    ... )
    >>> doc.id
    'index'
    """

    id: str
    title: str
    tree: SectionNode


InlineNode = t.Annotated[
    TextNode | EmphasisNode | StrongNode | LiteralNode | ReferenceNode | ImageNode,
    Field(discriminator="type"),
]
"""Discriminated union of nodes that may appear in an inline (phrase) context."""

BlockNode = t.Annotated[
    ParagraphNode
    | SectionNode
    | LiteralBlockNode
    | CommentNode
    | TransitionNode
    | BlockQuoteNode
    | BulletListNode
    | EnumeratedListNode
    | AdmonitionNode,
    Field(discriminator="type"),
]
"""Discriminated union of nodes that may appear in a block (body) context."""


EmphasisNode.model_rebuild()
StrongNode.model_rebuild()
ReferenceNode.model_rebuild()
ParagraphNode.model_rebuild()
SectionNode.model_rebuild()
BlockQuoteNode.model_rebuild()
ListItemNode.model_rebuild()
AdmonitionNode.model_rebuild()
