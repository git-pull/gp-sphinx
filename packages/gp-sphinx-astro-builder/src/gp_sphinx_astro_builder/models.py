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


class DefinitionListItemNode(BaseModel):
    """One entry in a definition list, pairing a term with a definition.

    The ``term`` slot accepts inline content (emphasis, strong, literal,
    references…); the ``definition`` slot accepts block content (paragraphs,
    lists, code blocks…). docutils also supports optional ``classifier``
    nodes between term and definition; we omit them here and revisit when a
    real document needs them.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import DefinitionListItemNode
    >>> node = DefinitionListItemNode.model_validate(
    ...     {
    ...         "type": "definitionListItem",
    ...         "term": [{"type": "text", "value": "foo"}],
    ...         "definition": [
    ...             {
    ...                 "type": "paragraph",
    ...                 "children": [{"type": "text", "value": "x"}],
    ...             },
    ...         ],
    ...     },
    ... )
    >>> node.term[0].value
    'foo'
    """

    type: t.Literal["definitionListItem"]
    term: list[InlineNode]
    definition: list[BlockNode]


class DefinitionListNode(BaseModel):
    """A definition list whose children are typed as definition_list_item.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import DefinitionListNode
    >>> node = DefinitionListNode.model_validate(
    ...     {"type": "definitionList", "children": []},
    ... )
    >>> node.children
    []
    """

    type: t.Literal["definitionList"]
    children: list[DefinitionListItemNode]


class SymbolRefNode(BaseModel):
    """A block-level placeholder pointing to an entry in ``symbols.json``.

    The autodoc directive (``.. autofunction::`` etc.) emits a ``desc`` node
    that the translator replaces with a :class:`SymbolRefNode`. The actual
    symbol payload is accumulated separately and written to
    ``src/content/api/symbols.json``; the renderer joins the two via the
    ``symbolId`` foreign key.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import SymbolRefNode
    >>> node = SymbolRefNode.model_validate(
    ...     {"type": "symbolRef", "symbolId": "x.y.foo"},
    ... )
    >>> node.symbolId
    'x.y.foo'
    """

    type: t.Literal["symbolRef"]
    symbolId: str


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
    | AdmonitionNode
    | DefinitionListNode
    | SymbolRefNode,
    Field(discriminator="type"),
]
"""Discriminated union of nodes that may appear in a block (body) context."""


# ─── Symbol models (top-level entries in src/content/api/symbols.json)


ParameterKind = t.Literal[
    "positional",
    "keyword",
    "var_positional",
    "var_keyword",
]
"""Allowed values for :attr:`Parameter.kind`.

The four kinds correspond to docutils-side classifications of how the
parameter is bound: positional-only, keyword-only (or positional-or-keyword
in autodoc's loose sense), ``*args``, and ``**kwargs``.
"""


SymbolKind = t.Literal[
    "function",
    "class",
    "method",
    "attribute",
    "property",
    "enum",
    "dataclass",
    "module",
]
"""Allowed values for :attr:`Symbol.kind`.

Mirrors the eight Python-domain object types that ``sphinx.ext.autodoc``
emits as ``desc`` nodes. Custom symbol kinds (CLI commands, MCP tools,
pytest fixtures) carry their own node types and are emitted by the
respective ``sphinx-autodoc-*`` extensions in their own per-extension
schemas.
"""


class Parameter(BaseModel):
    """One parameter in a callable signature.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import Parameter
    >>> p = Parameter(name="x", annotation="int", default="0", kind="positional")
    >>> p.kind
    'positional'
    """

    name: str
    annotation: str | None
    default: str | None
    kind: ParameterKind


class SymbolSource(BaseModel):
    """Source-location pointer for a symbol.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import SymbolSource
    >>> SymbolSource(repo="x", path="y.py", line=1).line
    1
    """

    repo: str
    path: str
    line: int


class Symbol(BaseModel):
    """One API symbol — function, class, method, etc. — emitted by autodoc.

    The ``id`` field is the fully-qualified import path
    (e.g. ``"gp_sphinx.config.merge_sphinx_config"``) and is the join key
    referenced by :class:`SymbolRefNode.symbolId`. The ``docstring_body``
    field holds the parsed doctree of the docstring's body, so the same
    ``<Node>`` renderer that handles top-level documents handles docstrings.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import Symbol
    >>> s = Symbol(
    ...     id="x.y.foo",
    ...     kind="function",
    ...     name="foo",
    ...     qualname="foo",
    ...     module="x.y",
    ...     signature="()",
    ...     parameters=[],
    ...     returns=None,
    ...     docstring_summary="Hi.",
    ...     docstring_body=[],
    ...     source=None,
    ... )
    >>> s.id
    'x.y.foo'
    """

    id: str
    kind: SymbolKind
    name: str
    qualname: str
    module: str
    signature: str
    parameters: list[Parameter]
    returns: str | None
    docstring_summary: str
    docstring_body: list[BlockNode]
    source: SymbolSource | None


EmphasisNode.model_rebuild()
StrongNode.model_rebuild()
ReferenceNode.model_rebuild()
ParagraphNode.model_rebuild()
SectionNode.model_rebuild()
BlockQuoteNode.model_rebuild()
ListItemNode.model_rebuild()
AdmonitionNode.model_rebuild()
DefinitionListItemNode.model_rebuild()
Symbol.model_rebuild()
