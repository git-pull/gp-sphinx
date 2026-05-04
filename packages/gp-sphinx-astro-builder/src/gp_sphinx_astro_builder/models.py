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

    The ``classes`` field carries Sphinx's xref-role markers
    (``xref`` / ``py-func`` / ``std-term`` / …) when the source reference
    came from a domain role like ``:py:func:`foo``` or ``:term:`foo```. The
    Astro renderer emits them as ``class="..."`` on the ``<a>`` so CSS can
    style each role distinctly (italic glossary terms, monospace type
    references, etc.). External links and Sphinx-internal cross-doc links
    typically carry no xref classes and the field is empty.

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
    classes: list[str] = []
    children: list[InlineNode]


FootnoteKind = t.Literal["footnote", "citation"]
"""Whether a footnote-shaped node carries a numeric footnote or a named citation.

docutils splits ``footnote`` and ``citation`` into separate node classes, but
Astro renders them with the same chrome (``<sup>`` jump for the inline ref,
``<aside>`` block for the body) — only the CSS class differs. We collapse the
two onto one model and discriminate on this field at render time.
"""


class FootnoteReferenceNode(BaseModel):
    """An inline footnote or citation reference (the bracketed superscript).

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import FootnoteReferenceNode
    >>> node = FootnoteReferenceNode.model_validate(
    ...     {
    ...         "type": "footnoteReference",
    ...         "kind": "footnote",
    ...         "href": "#footnote-1",
    ...         "label": "1",
    ...     },
    ... )
    >>> node.kind
    'footnote'
    """

    type: t.Literal["footnoteReference"]
    kind: FootnoteKind
    href: str
    label: str


BadgeSize = t.Literal["xxs", "xs", "sm", "md", "lg", "xl"]
"""Allowed values for :attr:`BadgeNode.size`.

Mirrors the size tokens in
:mod:`sphinx_ux_badges._nodes._BADGE_SIZES`. Each value maps to a CSS
modifier class (``gp-sphinx-badge--size-<value>``) that the theme styles.
"""

BadgeStyle = t.Literal["full", "icon-only", "inline-icon", "filled", "outline"]
"""Allowed values for :attr:`BadgeNode.style`.

The default ``"full"`` keeps the badge's chrome visible; the four other
variants correspond to the structural and fill variants the
:mod:`sphinx_ux_badges` extension exposes.
"""


class BadgeNode(BaseModel):
    """An inline badge produced by :mod:`sphinx_ux_badges`.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import BadgeNode
    >>> badge = BadgeNode(
    ...     type="badge",
    ...     text="readonly",
    ...     tooltip="Read-only operation",
    ... )
    >>> badge.style
    'full'
    """

    type: t.Literal["badge"]
    text: str
    tooltip: str | None = None
    icon: str | None = None
    size: BadgeSize | None = None
    style: BadgeStyle = "full"
    classes: list[str] = []
    """Modifier CSS classes attached to the badge.

    The ``sphinx_ux_badges`` Sphinx extension lets directive authors
    pass per-call ``classes=[...]`` such as
    ``gp-sphinx-badge--type-function`` /
    ``gp-sphinx-badge--state-deprecated`` /
    ``gp-sphinx-badge--scope-class`` /
    ``gp-sphinx-badge--mod-async``. The Astro renderer concatenates
    these with the base ``gp-sphinx-badge`` + style + size classes
    so per-domain CSS palettes can target each role distinctly. The
    field defaults to an empty list so existing wire-format payloads
    without it continue to validate.
    """


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


class RubricNode(BaseModel):
    """A short section label like ``Examples`` / ``Notes`` / ``See Also``.

    Sphinx's ``rubric`` directive — and the ``rubric`` node that NumPy-style
    docstrings produce when their section headers are promoted — appears
    inside autodoc bodies as a small bold heading rather than as body
    prose. Furo themes them with ``<p class="rubric">``; we promote them
    to a first-class wire-format node so the renderer applies matching
    small-caps section-header styling that distinguishes them from regular
    paragraphs.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import RubricNode
    >>> RubricNode(type="rubric", text="Examples").text
    'Examples'
    """

    type: t.Literal["rubric"]
    text: str


class TableCellNode(BaseModel):
    """One cell in a docutils table — the equivalent of an ``<entry>`` node.

    The ``header`` flag distinguishes ``<th>`` (rows from ``<thead>``)
    from ``<td>`` (rows from ``<tbody>``); the renderer dispatches on
    that flag rather than on a parent-row enum so a single
    discriminator stays sufficient.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import TableCellNode
    >>> TableCellNode(type="tableCell", header=True, children=[]).header
    True
    """

    type: t.Literal["tableCell"]
    header: bool
    children: list[BlockNode]


class TableRowNode(BaseModel):
    """One row in a docutils table — the equivalent of a ``<row>`` node.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import TableRowNode
    >>> TableRowNode(type="tableRow", cells=[]).type
    'tableRow'
    """

    type: t.Literal["tableRow"]
    cells: list[TableCellNode]


class TableNode(BaseModel):
    """A docutils table with separate head + body row groups.

    docutils emits ``table > tgroup > (thead, tbody) > row > entry``;
    we collapse the ``tgroup`` wrapper (no semantic role beyond
    grouping ``thead`` + ``tbody``) and surface ``head`` + ``body``
    as parallel arrays of rows. Empty ``head`` is valid for tables
    without a header row.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import TableNode
    >>> TableNode(type="table", head=[], body=[]).type
    'table'
    """

    type: t.Literal["table"]
    head: list[TableRowNode]
    body: list[TableRowNode]


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
    "versionadded",
    "versionchanged",
    "deprecated",
]
"""Allowed values for :attr:`AdmonitionNode.variant`.

The first nine variants correspond one-to-one with docutils' typed admonition
node classes (``nodes.note``, ``nodes.warning``, etc.). The three ``version*``
variants come from Sphinx's ``versionmodified`` node, which is collapsed onto
the same Pydantic model so the Astro renderer dispatches on one component
instead of twelve.
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


ApiLayoutComponent = t.Literal[
    "region",
    "fold",
    "sig_fold",
    "component",
    "inline_component",
    "slot",
    "permalink",
]
"""Allowed values for :attr:`ApiLayoutNode.component`.

Mirrors the seven custom node types ``sphinx-ux-autodoc-layout`` registers
(``api_region``, ``api_fold``, ``api_sig_fold``, ``api_component``,
``api_inline_component``, ``api_slot``, ``api_permalink``) so the
TypeScript renderer dispatches on a single field rather than seven
separate component classes.
"""


class ApiLayoutNode(BaseModel):
    """A layout primitive emitted by :mod:`sphinx_ux_autodoc_layout`.

    The seven custom node types from that extension share a common shape:
    a structural wrapper carrying optional name/tag/kind/summary/etc.
    attributes plus block children. Modelling them as a single discriminated
    container lets the Astro renderer dispatch on ``component`` without
    needing seven near-identical Pydantic classes.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import ApiLayoutNode
    >>> region = ApiLayoutNode(
    ...     type="apiLayout",
    ...     component="region",
    ...     kind="narrative",
    ... )
    >>> region.component
    'region'
    """

    type: t.Literal["apiLayout"]
    component: ApiLayoutComponent
    name: str | None = None
    tag: str | None = None
    kind: str | None = None
    summary: str | None = None
    href: str | None = None
    title: str | None = None
    slot: str | None = None
    open: bool = False
    classes: list[str] = []
    children: list[BlockNode] = []


CliCommandComponent = t.Literal[
    "program",
    "usage",
    "group",
    "argument",
    "subcommands",
    "subcommand",
]
"""Allowed values for :attr:`CliCommandNode.component`.

Mirrors the six custom node types ``sphinx-autodoc-argparse`` registers
(``argparse_program``, ``argparse_usage``, ``argparse_group``,
``argparse_argument``, ``argparse_subcommands``, ``argparse_subcommand``)
so the TypeScript renderer dispatches on a single field rather than six
separate component classes.
"""


class CliCommandNode(BaseModel):
    """A CLI documentation primitive emitted by :mod:`sphinx_autodoc_argparse`.

    The six custom node types from that extension share a structural shape:
    a wrapper carrying optional argparse-derived attributes (program name,
    usage line, argument names, default values, choices, subcommand
    aliases…) plus block children. Modelling them as a single discriminated
    container lets the Astro renderer dispatch on ``component`` without
    needing six near-identical Pydantic classes.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import CliCommandNode
    >>> arg = CliCommandNode(
    ...     type="cliCommand",
    ...     component="argument",
    ...     names=["-v", "--verbose"],
    ...     help="Increase output verbosity",
    ... )
    >>> arg.names
    ['-v', '--verbose']
    """

    type: t.Literal["cliCommand"]
    component: CliCommandComponent
    prog: str | None = None
    usage: str | None = None
    title: str | None = None
    description: str | None = None
    names: list[str] = []
    help: str | None = None
    default: str | None = None
    choices: list[str] = []
    required: bool = False
    metavar: str | None = None
    name: str | None = None
    aliases: list[str] = []
    classes: list[str] = []
    children: list[BlockNode] = []


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
    title: list[InlineNode] | None = None
    """Custom inline label for the admonition.

    MyST's ``:::{admonition} Foo :class: warning`` syntax (and the
    docutils ``.. admonition:: Foo`` directive) lets the author
    provide a free-form title that overrides the variant's default
    label. Typed admonitions (``:::{warning}``, ``.. note::``) carry
    no custom label, so this field is ``None``; the renderer falls
    back to the variant's own name in that case.
    """
    children: list[BlockNode]


class FootnoteNode(BaseModel):
    """A block-level footnote or citation body.

    Pairs a ``label`` (the bracketed identifier rendered alongside the body)
    with a stable ``id`` (the anchor target a ``FootnoteReferenceNode`` jumps
    to) and a list of block children — typically a single paragraph but
    docutils permits multiple blocks for rich citations.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import FootnoteNode
    >>> node = FootnoteNode.model_validate(
    ...     {
    ...         "type": "footnote",
    ...         "kind": "footnote",
    ...         "id": "footnote-1",
    ...         "label": "1",
    ...         "children": [
    ...             {
    ...                 "type": "paragraph",
    ...                 "children": [{"type": "text", "value": "x"}],
    ...             },
    ...         ],
    ...     },
    ... )
    >>> node.label
    '1'
    """

    type: t.Literal["footnote"]
    kind: FootnoteKind
    id: str
    label: str
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
    TextNode
    | EmphasisNode
    | StrongNode
    | LiteralNode
    | ReferenceNode
    | FootnoteReferenceNode
    | ImageNode
    | BadgeNode,
    Field(discriminator="type"),
]
"""Discriminated union of nodes that may appear in an inline (phrase) context."""

BlockNode = t.Annotated[
    ParagraphNode
    | SectionNode
    | LiteralBlockNode
    | CommentNode
    | TransitionNode
    | RubricNode
    | TableNode
    | BlockQuoteNode
    | BulletListNode
    | EnumeratedListNode
    | AdmonitionNode
    | FootnoteNode
    | DefinitionListNode
    | SymbolRefNode
    | ApiLayoutNode
    | CliCommandNode,
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
    "exception",
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


class XrefEntry(BaseModel):
    """One entry in the cross-reference index.

    Mirrors what Sphinx writes to ``objects.inv``: each entry pairs a
    fully-qualified target (``"gp_sphinx.config.merge_sphinx_config"``)
    with the URL that resolves it on the rendered site, scoped by the
    ``domain`` it lives in (``"py"``, ``"std"``, ``"c"``…) and the
    ``role`` that introduced it (``"func"``, ``"class"``, ``"data"``…).

    The ``id`` field is the canonical join key — typically
    ``f"{domain}:{role}:{target}"`` — so a downstream Astro site can
    look up an entry without parsing.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import XrefEntry
    >>> entry = XrefEntry(
    ...     id="py:func:foo",
    ...     domain="py",
    ...     role="func",
    ...     target="foo",
    ...     href="/api/foo/",
    ... )
    >>> entry.priority
    0
    """

    id: str
    domain: str
    role: str
    target: str
    href: str
    display: str | None = None
    priority: int = 0


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
FootnoteNode.model_rebuild()
DefinitionListItemNode.model_rebuild()
ApiLayoutNode.model_rebuild()
CliCommandNode.model_rebuild()
TableCellNode.model_rebuild()
TableRowNode.model_rebuild()
TableNode.model_rebuild()
Symbol.model_rebuild()
