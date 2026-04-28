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
    TextNode | EmphasisNode,
    Field(discriminator="type"),
]
"""Discriminated union of nodes that may appear in an inline (phrase) context."""

BlockNode = t.Annotated[
    ParagraphNode | SectionNode,
    Field(discriminator="type"),
]
"""Discriminated union of nodes that may appear in a block (body) context."""


EmphasisNode.model_rebuild()
ParagraphNode.model_rebuild()
SectionNode.model_rebuild()
