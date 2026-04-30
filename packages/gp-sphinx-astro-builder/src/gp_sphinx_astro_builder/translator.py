"""Docutils-to-typed-JSON translator for the AstroBuilder.

The translator is a :class:`docutils.nodes.SparseNodeVisitor` subclass: each
``visit_<tagname>`` pushes a frame onto an internal stack; each
``depart_<tagname>`` pops the frame, attaches its accumulated children to the
parent frame's appropriate slot, and lets traversal continue. Unknown nodes
fall through to ``unknown_visit`` / ``unknown_departure``, which are
inherited no-ops, so the translator never crashes on an unhandled node type.

The accumulated tree is finalised in :meth:`DocTreeJSONTranslator.result`,
which validates the dict through :class:`Document` and returns the typed
model.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pathlib
import typing as t

from docutils import nodes
from sphinx import addnodes

from gp_sphinx_astro_builder.models import Document, Symbol
from gp_sphinx_astro_builder.symbols import normalize_symbol_kind

_log = logging.getLogger(__name__)


def normalize_doc_href(href: str) -> str:
    """Rewrite a docutils refuri to a canonical Astro route URL.

    The ``AstroBuilder`` declares ``.json`` as its output suffix, so
    Sphinx-resolved refuris look like ``packages/gp-sphinx.json#api``.
    The rendered HTML lives at trailing-slash routes
    (``/packages/gp-sphinx/``) — leaving the raw refuri in the doctree
    would point readers at the JSON content payload rather than the
    rendered page.

    External URLs (``https://…``), in-page anchors (``#id``), the empty
    string, and any path that doesn't end in ``.json`` (or
    ``.json#fragment``) pass through untouched.

    Examples
    --------
    >>> normalize_doc_href("packages/gp-sphinx.json#api")
    '/packages/gp-sphinx/#api'
    >>> normalize_doc_href("index.json")
    '/'
    >>> normalize_doc_href("https://example.com/page")
    'https://example.com/page'
    """
    if href == "" or href.startswith(("http://", "https://", "//", "#", "mailto:")):
        return href
    fragment = ""
    path = href
    if "#" in path:
        path, fragment = path.split("#", 1)
        fragment = f"#{fragment}"
    if not path.endswith(".json"):
        return href
    slug = path.removesuffix(".json")
    if slug == "index":
        return f"/{fragment}"
    if slug.endswith("/index"):
        slug = slug[: -len("/index")]
    return f"/{slug}/{fragment}"


def _resolve_symbol_source(
    *,
    module_name: str,
    fullname: str,
    repo_url: str,
    source_root: pathlib.Path,
) -> dict[str, t.Any] | None:
    """Look up a Python object's source file + line via :mod:`inspect`.

    Returns a ``SymbolSource``-shaped dict or ``None`` when any step
    fails. We never raise — a missing import or an unfindable source
    file shouldn't fail the doc build, just leave ``Symbol.source`` as
    ``null`` like before.
    """
    if module_name == "" or repo_url == "":
        return None
    try:
        module = importlib.import_module(module_name)
    except Exception:
        _log.debug("could not import %r for source lookup", module_name)
        return None
    obj: t.Any = module
    if fullname != "":
        try:
            for part in fullname.split("."):
                obj = getattr(obj, part)
        except AttributeError:
            return None
    try:
        sourcefile = inspect.getsourcefile(obj)
        _, line = inspect.getsourcelines(obj)
    except (OSError, TypeError):
        return None
    if sourcefile is None:
        return None
    try:
        relpath = pathlib.Path(sourcefile).resolve().relative_to(source_root.resolve())
    except ValueError:
        return None
    return {
        "repo": repo_url,
        "path": str(relpath),
        "line": int(line),
    }


if t.TYPE_CHECKING:
    from sphinx.builders import Builder

    from gp_sphinx_astro_builder.symbols import SymbolAccumulator


_BLOCK_CONTEXT_FRAMES: frozenset[str] = frozenset(
    {
        "section",
        "listItem",
        "blockQuote",
        "admonition",
        "definition",
        "desc_content",
        # Footnote and citation bodies declare ``children: list[BlockNode]``
        # so paragraph-wrap any inline content (rare, but possible if a
        # citation body somehow holds bare text).
        "footnote",
        # Frames pushed by extension JSON visitors. ``apiLayout`` and
        # ``cliCommand`` both declare ``children: list[BlockNode]`` in
        # their Pydantic models, so any inline content that lands inside
        # them — typically the signature literals + badges that
        # ``sphinx-ux-autodoc-layout`` and ``sphinx-ux-badges`` emit —
        # has to be paragraph-wrapped before validation.
        "apiLayout",
        "cliCommand",
    },
)
"""Frame kinds whose ``children`` slot may only hold ``BlockNode`` payloads.

When :meth:`DocTreeJSONTranslator.append_node` is asked to attach an inline
typed-JSON dict to a frame in this set, it wraps the inline data in an
implicit paragraph (or merges it into a trailing paragraph). That keeps
the wire format's inline/block split intact even when source documents
emit inline content directly into a block context — common with
``sphinx-design`` cards, ``container`` directives, custom directives that
produce ``PassthroughTextElement``, and the toctree's expanded
``compact_paragraph`` chain.
"""

_INLINE_TYPES: frozenset[str] = frozenset(
    {
        "text",
        "literal",
        "emphasis",
        "strong",
        "reference",
        "footnoteReference",
        "image",
        "badge",
    },
)
"""Wire-format ``type`` discriminators that count as inline."""


def _has_block_children(node: nodes.Element) -> bool:
    """Return ``True`` if ``node`` contains at least one block-level child.

    Used to dispatch ``compact_paragraph`` between paragraph-wrap and
    pass-through modes. We can't use ``isinstance(c, nodes.Body)`` because
    docutils' ``reference`` (and ``image``) inherit *both* ``Inline`` and
    ``Body`` via the ``General`` group — so ``Body`` membership is not a
    block discriminator. Inverting the check (non-inline = block) handles
    that correctly: ``Text`` and any subclass of ``nodes.Inline`` count as
    inline, everything else (paragraph, bullet_list, …) counts as block.
    """
    return any(
        not isinstance(child, (nodes.Inline, nodes.Text)) for child in node.children
    )


_FrameKind = t.Literal[
    "section",
    "title",
    "paragraph",
    "emphasis",
    "strong",
    "literal",
    "reference",
    "blockQuote",
    "bulletList",
    "enumeratedList",
    "listItem",
    "admonition",
    "footnote",
    "definitionList",
    "definitionListItem",
    "term",
    "definition",
    "desc",
    "desc_content",
]


class _Frame(t.TypedDict):
    """Stack frame collected during traversal."""

    kind: _FrameKind
    data: dict[str, t.Any]


class DocTreeJSONTranslator(nodes.SparseNodeVisitor):
    """Walk a docutils doctree and accumulate a Pydantic-validated ``Document``.

    Parameters
    ----------
    document
        The docutils document being walked. Required by the
        :class:`~docutils.nodes.NodeVisitor` base class.
    builder
        The Sphinx builder driving the walk, when invoked from a Sphinx build.
        ``None`` for direct tree-unit invocation.
    docname
        The Sphinx docname for the document. Falls back to ``builder
        .current_docname`` when omitted and a builder is provided.

    Examples
    --------
    >>> import docutils.frontend, docutils.parsers.rst, docutils.utils
    >>> from docutils import nodes
    >>> from gp_sphinx_astro_builder.translator import DocTreeJSONTranslator
    >>> settings = docutils.frontend.OptionParser(
    ...     components=(docutils.parsers.rst.Parser,),
    ... ).get_default_values()
    >>> doc = docutils.utils.new_document("<doctest>", settings)
    >>> section = nodes.section(ids=["s"])
    >>> title = nodes.title()
    >>> title += nodes.Text("Hi")
    >>> section += title
    >>> doc += section
    >>> translator = DocTreeJSONTranslator(doc, docname="d")
    >>> _ = doc.walkabout(translator)
    >>> translator.result().title
    'Hi'
    """

    def __init__(
        self,
        document: nodes.document,
        builder: Builder | None = None,
        *,
        docname: str = "",
        symbol_accumulator: SymbolAccumulator | None = None,
    ) -> None:
        super().__init__(document)
        self._builder = builder
        if not docname and builder is not None:
            docname = getattr(builder, "current_docname", "") or ""
        if symbol_accumulator is None and builder is not None:
            symbol_accumulator = getattr(builder, "_symbol_accumulator", None)
        self._docname = docname
        self._symbol_accumulator = symbol_accumulator
        self._stack: list[_Frame] = []
        self._tree: dict[str, t.Any] | None = None
        self._doc_title: str = ""

    def result(self) -> Document:
        """Return the accumulated tree as a validated :class:`Document`.

        Raises
        ------
        RuntimeError
            If the document has no top-level section.
        """
        if self._tree is None:
            msg = "doctree had no top-level section to translate"
            raise RuntimeError(msg)
        return Document.model_validate(
            {"id": self._docname, "title": self._doc_title, "tree": self._tree},
        )

    def visit_section(self, node: nodes.Element) -> None:
        """Open a new section frame."""
        ids = node.get("ids") or []
        section_id = ids[0] if ids else ""
        self._stack.append(
            {
                "kind": "section",
                "data": {
                    "type": "section",
                    "id": section_id,
                    "title": [],
                    "children": [],
                },
            },
        )

    def depart_section(self, node: nodes.Element) -> None:
        """Close the current section, attaching it to its parent."""
        frame = self._stack.pop()
        section_data = frame["data"]
        if self._stack:
            self._stack[-1]["data"]["children"].append(section_data)
        else:
            self._tree = section_data

    def visit_title(self, node: nodes.Element) -> None:
        """Open a title frame whose children become the parent section's title."""
        self._stack.append({"kind": "title", "data": {"children": []}})

    def depart_title(self, node: nodes.Element) -> None:
        """Attach the title's collected inline children to the parent section."""
        frame = self._stack.pop()
        title_children: list[dict[str, t.Any]] = frame["data"]["children"]
        if self._stack:
            self._stack[-1]["data"]["title"] = title_children
        if not self._doc_title:
            self._doc_title = "".join(
                child["value"]
                for child in title_children
                if child.get("type") == "text"
            )

    def visit_paragraph(self, node: nodes.Element) -> None:
        """Open a paragraph frame."""
        self._stack.append(
            {
                "kind": "paragraph",
                "data": {"type": "paragraph", "children": []},
            },
        )

    def depart_paragraph(self, node: nodes.Element) -> None:
        """Close the paragraph and attach it to the parent block frame."""
        frame = self._stack.pop()
        self._stack[-1]["data"]["children"].append(frame["data"])

    # Sphinx's toctree, captioned figures, and a handful of other directives
    # wrap content in a ``compact_paragraph`` rather than a regular
    # ``paragraph``. The trouble is the wrapper is overloaded: at the inner
    # level (``list_item / compact_paragraph / reference``) it carries inline
    # content and must be wrapped as a ``paragraph``; at the outer level
    # (``section / compact_paragraph / bullet_list``) it carries a
    # block-level child and must be transparent so the bullet_list attaches
    # to the parent section directly. We dispatch on children: block-bearing
    # compact_paragraphs become pass-through, inline-bearing ones become
    # paragraphs.
    def visit_compact_paragraph(self, node: nodes.Element) -> None:
        """Open a paragraph frame, or pass through when wrapping block content."""
        if _has_block_children(node):
            node["_astro_skip_frame"] = True
            return
        self.visit_paragraph(node)

    def depart_compact_paragraph(self, node: nodes.Element) -> None:
        """Close the paragraph frame, unless this compact_paragraph was skipped."""
        if node.get("_astro_skip_frame", False):
            return
        self.depart_paragraph(node)

    def visit_emphasis(self, node: nodes.Element) -> None:
        """Open an emphasis frame."""
        self._stack.append(
            {
                "kind": "emphasis",
                "data": {"type": "emphasis", "children": []},
            },
        )

    def depart_emphasis(self, node: nodes.Element) -> None:
        """Close the emphasis run and attach it to the parent inline collector."""
        frame = self._stack.pop()
        self.append_node(frame["data"])

    def visit_strong(self, node: nodes.Element) -> None:
        """Open a strong-emphasis frame."""
        self._stack.append(
            {
                "kind": "strong",
                "data": {"type": "strong", "children": []},
            },
        )

    def depart_strong(self, node: nodes.Element) -> None:
        """Close the strong run and attach it to the parent inline collector."""
        frame = self._stack.pop()
        self.append_node(frame["data"])

    def visit_literal(self, node: nodes.Element) -> None:
        """Capture a literal run's text value and skip child traversal.

        Raises
        ------
        docutils.nodes.SkipChildren
            Always: literal text is captured via :meth:`docutils.nodes.Element.astext`
            on visit, so traversing the inner ``Text`` child would double-count.
        """
        self._stack.append(
            {
                "kind": "literal",
                "data": {"type": "literal", "value": node.astext()},
            },
        )
        raise nodes.SkipChildren

    def depart_literal(self, node: nodes.Element) -> None:
        """Close the literal run and attach it to the parent inline collector."""
        frame = self._stack.pop()
        self.append_node(frame["data"])

    def visit_reference(self, node: nodes.Element) -> None:
        """Open a reference frame, normalising refuri / refid into one href.

        Sphinx-resolved refuris that target other docs end with the
        builder's ``.json`` output suffix (e.g.
        ``packages/gp-sphinx.json#api``); ``normalize_doc_href``
        rewrites these to the canonical site routes
        (``/packages/gp-sphinx/#api``) so clicking lands on the
        rendered HTML page instead of the JSON content payload.
        """
        refuri = node.get("refuri")
        refid = node.get("refid")
        if refuri:
            href = normalize_doc_href(refuri)
        elif refid:
            href = f"#{refid}"
        else:
            href = ""
        self._stack.append(
            {
                "kind": "reference",
                "data": {
                    "type": "reference",
                    "href": href,
                    "children": [],
                },
            },
        )

    def depart_reference(self, node: nodes.Element) -> None:
        """Close the reference and attach it to the parent collector."""
        frame = self._stack.pop()
        self.append_node(frame["data"])

    def visit_image(self, node: nodes.Element) -> None:
        """Append an image leaf node to the current inline collector.

        Raises
        ------
        docutils.nodes.SkipNode
            Always: ``image`` is a leaf in docutils — there are no children
            to traverse and no closing handler is needed.
        """
        self.append_node(
            {
                "type": "image",
                "uri": node.get("uri", ""),
                "alt": node.get("alt"),
            },
        )
        raise nodes.SkipNode

    def visit_literal_block(self, node: nodes.Element) -> None:
        """Append a fenced code block to the parent block collector.

        Raises
        ------
        docutils.nodes.SkipNode
            Always: literal_block carries its content as a single Text child;
            we capture it via :meth:`docutils.nodes.Element.astext` on visit
            and skip both child traversal and the depart handler.
        """
        if self._stack:
            self._stack[-1]["data"]["children"].append(
                {
                    "type": "literalBlock",
                    "language": node.get("language"),
                    "code": node.astext(),
                },
            )
        raise nodes.SkipNode

    def visit_comment(self, node: nodes.Element) -> None:
        """Append a comment block, preserving its raw text.

        Raises
        ------
        docutils.nodes.SkipNode
            Always: comment is a fixed-text element captured via
            :meth:`docutils.nodes.Element.astext` on visit.
        """
        if self._stack:
            self._stack[-1]["data"]["children"].append(
                {"type": "comment", "value": node.astext()},
            )
        raise nodes.SkipNode

    def visit_transition(self, node: nodes.Element) -> None:
        """Append a payload-less transition marker to the parent block collector.

        Raises
        ------
        docutils.nodes.SkipNode
            Always: transition is an empty element; no children to walk.
        """
        if self._stack:
            self._stack[-1]["data"]["children"].append({"type": "transition"})
        raise nodes.SkipNode

    def visit_block_quote(self, node: nodes.Element) -> None:
        """Open a block_quote frame."""
        self._stack.append(
            {
                "kind": "blockQuote",
                "data": {"type": "blockQuote", "children": []},
            },
        )

    def depart_block_quote(self, node: nodes.Element) -> None:
        """Close the block_quote and attach it to the parent block collector."""
        frame = self._stack.pop()
        self._stack[-1]["data"]["children"].append(frame["data"])

    def visit_bullet_list(self, node: nodes.Element) -> None:
        """Open a bullet_list frame."""
        self._stack.append(
            {
                "kind": "bulletList",
                "data": {"type": "bulletList", "children": []},
            },
        )

    def depart_bullet_list(self, node: nodes.Element) -> None:
        """Close the bullet_list and attach it to the parent block collector."""
        frame = self._stack.pop()
        self._stack[-1]["data"]["children"].append(frame["data"])

    def visit_enumerated_list(self, node: nodes.Element) -> None:
        """Open an enumerated_list frame, capturing the optional ``start`` index."""
        start_value = node.get("start")
        data: dict[str, t.Any] = {
            "type": "enumeratedList",
            "start": start_value if isinstance(start_value, int) else None,
            "children": [],
        }
        self._stack.append({"kind": "enumeratedList", "data": data})

    def depart_enumerated_list(self, node: nodes.Element) -> None:
        """Close the enumerated_list and attach to the parent block collector."""
        frame = self._stack.pop()
        self._stack[-1]["data"]["children"].append(frame["data"])

    def visit_list_item(self, node: nodes.Element) -> None:
        """Open a list_item frame."""
        self._stack.append(
            {
                "kind": "listItem",
                "data": {"type": "listItem", "children": []},
            },
        )

    def depart_list_item(self, node: nodes.Element) -> None:
        """Close the list_item and attach it to the parent list collector."""
        frame = self._stack.pop()
        self._stack[-1]["data"]["children"].append(frame["data"])

    def _open_admonition(self, variant: str) -> None:
        """Push an admonition frame with the given variant tag."""
        self._stack.append(
            {
                "kind": "admonition",
                "data": {
                    "type": "admonition",
                    "variant": variant,
                    "children": [],
                },
            },
        )

    def _close_admonition(self) -> None:
        """Pop the current admonition frame and attach to the parent."""
        frame = self._stack.pop()
        self._stack[-1]["data"]["children"].append(frame["data"])

    def visit_note(self, node: nodes.Element) -> None:
        """Open a note admonition frame."""
        self._open_admonition("note")

    def depart_note(self, node: nodes.Element) -> None:
        """Close the note admonition frame."""
        self._close_admonition()

    def visit_warning(self, node: nodes.Element) -> None:
        """Open a warning admonition frame."""
        self._open_admonition("warning")

    def depart_warning(self, node: nodes.Element) -> None:
        """Close the warning admonition frame."""
        self._close_admonition()

    def visit_attention(self, node: nodes.Element) -> None:
        """Open an attention admonition frame."""
        self._open_admonition("attention")

    def depart_attention(self, node: nodes.Element) -> None:
        """Close the attention admonition frame."""
        self._close_admonition()

    def visit_caution(self, node: nodes.Element) -> None:
        """Open a caution admonition frame."""
        self._open_admonition("caution")

    def depart_caution(self, node: nodes.Element) -> None:
        """Close the caution admonition frame."""
        self._close_admonition()

    def visit_important(self, node: nodes.Element) -> None:
        """Open an important admonition frame."""
        self._open_admonition("important")

    def depart_important(self, node: nodes.Element) -> None:
        """Close the important admonition frame."""
        self._close_admonition()

    def visit_tip(self, node: nodes.Element) -> None:
        """Open a tip admonition frame."""
        self._open_admonition("tip")

    def depart_tip(self, node: nodes.Element) -> None:
        """Close the tip admonition frame."""
        self._close_admonition()

    def visit_hint(self, node: nodes.Element) -> None:
        """Open a hint admonition frame."""
        self._open_admonition("hint")

    def depart_hint(self, node: nodes.Element) -> None:
        """Close the hint admonition frame."""
        self._close_admonition()

    def visit_danger(self, node: nodes.Element) -> None:
        """Open a danger admonition frame."""
        self._open_admonition("danger")

    def depart_danger(self, node: nodes.Element) -> None:
        """Close the danger admonition frame."""
        self._close_admonition()

    def visit_error(self, node: nodes.Element) -> None:
        """Open an error admonition frame."""
        self._open_admonition("error")

    def depart_error(self, node: nodes.Element) -> None:
        """Close the error admonition frame."""
        self._close_admonition()

    def visit_versionmodified(self, node: nodes.Element) -> None:
        """Open an admonition frame for a Sphinx ``versionmodified`` node.

        Sphinx emits ``addnodes.versionmodified`` for the
        ``versionadded`` / ``versionchanged`` / ``deprecated`` directives,
        carrying the directive name in ``node["type"]``. We reuse the
        admonition node so the Astro renderer can theme the three
        directives consistently with the rest of the admonition family.
        """
        directive_type = node.get("type", "versionadded")
        if directive_type not in {"versionadded", "versionchanged", "deprecated"}:
            directive_type = "versionadded"
        self._open_admonition(directive_type)

    def depart_versionmodified(self, node: nodes.Element) -> None:
        """Close the version-modified admonition frame."""
        self._close_admonition()

    def _open_footnote(self, node: nodes.Element, kind: str) -> None:
        """Push a footnote / citation frame, extracting label + id from the node.

        docutils stores the label as a child ``<label>`` node and the anchor
        target on ``node["ids"]``. We pre-extract both so the body of the
        frame can be filled with regular block content via the standard
        block dispatch (``visit_paragraph``, ``visit_bullet_list``…).
        """
        node_ids = node.get("ids") or []
        target_id = node_ids[0] if node_ids else ""
        label_text = ""
        for child in node.children:
            if isinstance(child, nodes.label):
                label_text = child.astext()
                break
        self._stack.append(
            {
                "kind": "footnote",
                "data": {
                    "type": "footnote",
                    "kind": kind,
                    "id": target_id,
                    "label": label_text,
                    "children": [],
                },
            },
        )

    def _close_footnote(self) -> None:
        """Pop the current footnote frame and attach to the parent."""
        frame = self._stack.pop()
        self._stack[-1]["data"]["children"].append(frame["data"])

    def visit_footnote(self, node: nodes.Element) -> None:
        """Open a footnote frame; the label child is captured, others walk."""
        self._open_footnote(node, "footnote")

    def depart_footnote(self, node: nodes.Element) -> None:
        """Close the footnote frame."""
        self._close_footnote()

    def visit_citation(self, node: nodes.Element) -> None:
        """Open a citation frame (same chrome as footnote, different ``kind``)."""
        self._open_footnote(node, "citation")

    def depart_citation(self, node: nodes.Element) -> None:
        """Close the citation frame."""
        self._close_footnote()

    def visit_label(self, node: nodes.Element) -> None:
        """Skip the label child of a footnote / citation.

        Labels are pre-extracted in ``_open_footnote`` and stored on the
        footnote frame; rendering them again as a paragraph would duplicate
        the bracketed identifier in the output.
        """
        raise nodes.SkipNode

    def _emit_footnote_like_reference(
        self,
        node: nodes.Element,
        kind: str,
    ) -> None:
        """Append a ``footnoteReference`` inline node to the current frame."""
        refid = node.get("refid") or node.get("refname") or ""
        href = f"#{refid}" if refid else ""
        label_text = node.astext()
        self.append_node(
            {
                "type": "footnoteReference",
                "kind": kind,
                "href": href,
                "label": label_text,
            },
        )

    def visit_footnote_reference(self, node: nodes.Element) -> None:
        """Emit an inline ``footnoteReference`` jump anchor."""
        self._emit_footnote_like_reference(node, "footnote")
        raise nodes.SkipNode

    def depart_footnote_reference(self, node: nodes.Element) -> None:
        """No-op; ``visit_footnote_reference`` raises ``SkipNode``."""

    def visit_citation_reference(self, node: nodes.Element) -> None:
        """Emit an inline ``footnoteReference`` jump anchor with citation kind."""
        self._emit_footnote_like_reference(node, "citation")
        raise nodes.SkipNode

    def depart_citation_reference(self, node: nodes.Element) -> None:
        """No-op; ``visit_citation_reference`` raises ``SkipNode``."""

    def visit_definition_list(self, node: nodes.Element) -> None:
        """Open a definition_list frame."""
        self._stack.append(
            {
                "kind": "definitionList",
                "data": {"type": "definitionList", "children": []},
            },
        )

    def depart_definition_list(self, node: nodes.Element) -> None:
        """Close the definition_list and attach to the parent block collector."""
        frame = self._stack.pop()
        self._stack[-1]["data"]["children"].append(frame["data"])

    def visit_definition_list_item(self, node: nodes.Element) -> None:
        """Open a definition_list_item frame with empty term + definition slots."""
        self._stack.append(
            {
                "kind": "definitionListItem",
                "data": {
                    "type": "definitionListItem",
                    "term": [],
                    "definition": [],
                },
            },
        )

    def depart_definition_list_item(self, node: nodes.Element) -> None:
        """Close the definition_list_item, attaching to the definition_list."""
        frame = self._stack.pop()
        self._stack[-1]["data"]["children"].append(frame["data"])

    def visit_term(self, node: nodes.Element) -> None:
        """Open a term frame; its children become the parent item's term slot."""
        self._stack.append({"kind": "term", "data": {"children": []}})

    def depart_term(self, node: nodes.Element) -> None:
        """Attach collected inline children to the parent item's ``term`` slot."""
        frame = self._stack.pop()
        if self._stack:
            self._stack[-1]["data"]["term"] = frame["data"]["children"]

    def visit_definition(self, node: nodes.Element) -> None:
        """Open a definition frame; children become the parent item's definition."""
        self._stack.append({"kind": "definition", "data": {"children": []}})

    def depart_definition(self, node: nodes.Element) -> None:
        """Attach collected block children to the parent item's ``definition`` slot."""
        frame = self._stack.pop()
        if self._stack:
            self._stack[-1]["data"]["definition"] = frame["data"]["children"]

    # Sphinx's autodoc + sphinx-autodoc-typehints render NumPy docstring
    # rubrics (Parameters, Returns, Examples, …) as ``field_list / field /
    # field_name / field_body`` chains. The shape is exactly a definition
    # list: each ``field`` pairs an inline ``field_name`` (term) with
    # block ``field_body`` content (definition). Aliasing onto the
    # existing definition_list visitors avoids growing the wire format.
    visit_field_list = visit_definition_list
    depart_field_list = depart_definition_list
    visit_field = visit_definition_list_item
    depart_field = depart_definition_list_item
    visit_field_name = visit_term
    depart_field_name = depart_term
    visit_field_body = visit_definition
    depart_field_body = depart_definition

    # Sphinx renders NumPy "Examples", "Notes", "See Also" rubrics as
    # ``rubric`` nodes whose only child is the inline label text. Without
    # explicit handling, that bare ``Text`` leaks into the surrounding
    # block context — exactly the same failure mode as ``field_name``
    # before the field_list aliases above. Treating ``rubric`` as a
    # paragraph wraps the inline label correctly and preserves the
    # rubric's class list (e.g. ``classes=["rubric-h2"]``) for the
    # renderer to dispatch on if it cares about the visual hierarchy.
    visit_rubric = visit_paragraph
    depart_rubric = depart_paragraph

    # Generic structural wrappers that the JSON wire format does not
    # need to preserve. ``container`` (docutils' ``.. container::``,
    # also reused by ``sphinx-design`` for grids and cards) and
    # ``compound`` (the toctree's outer wrapper) are pass-through. So is
    # ``PassthroughTextElement`` from sphinx-design, which holds the
    # title text of a card. Their children attach to whatever real frame
    # is above on the stack; ``append_node`` then promotes inline content
    # into an implicit paragraph if that real frame is block-only.
    def visit_container(self, node: nodes.Element) -> None:
        """Pass through a ``container`` (no frame; children attach to parent)."""

    def depart_container(self, node: nodes.Element) -> None:
        """Companion no-op for :meth:`visit_container`."""

    def visit_compound(self, node: nodes.Element) -> None:
        """Pass through a ``compound`` (toctree wrapper)."""

    def depart_compound(self, node: nodes.Element) -> None:
        """Companion no-op for :meth:`visit_compound`."""

    def visit_PassthroughTextElement(self, node: nodes.Element) -> None:
        """Pass through sphinx-design's title-text wrapper."""

    def depart_PassthroughTextElement(self, node: nodes.Element) -> None:
        """Companion no-op for :meth:`visit_PassthroughTextElement`."""

    def append_node(self, data: dict[str, t.Any]) -> None:
        """Append a typed-JSON node dict to the current frame's children list.

        Public API for extensions that register JSON visitors via
        ``app.add_node(NodeCls, json=(visit, depart))``. Visitors call
        this to inject their serialised payload into the parent's
        children list, then ``raise nodes.SkipNode`` to skip the node's
        docutils subtree.

        Some frame shapes (the ``desc`` frame for autodoc symbols, the
        ``definitionListItem`` frame with its term/definition slots) do
        not expose a flat ``children`` list. Nodes that land inside one
        of those frames belong to a sub-section the translator hasn't
        pushed a proper frame for yet, so we drop them silently rather
        than crashing the build.

        When the parent frame is block-only (a ``section``, ``list_item``
        body, an ``admonition``, …) and ``data`` is an inline payload, the
        method wraps it in an implicit paragraph rather than letting the
        inline node leak into a block-context children list and fail
        Pydantic validation. Sequential inline payloads in the same block
        context merge into the trailing paragraph so they read as one
        run rather than a stack of single-word paragraphs.
        """
        if not self._stack:
            return
        parent_kind = self._stack[-1]["kind"]
        children = self._stack[-1]["data"].get("children")
        if not isinstance(children, list):
            return
        if parent_kind in _BLOCK_CONTEXT_FRAMES and data.get("type") in _INLINE_TYPES:
            if children and children[-1].get("type") == "paragraph":
                last_children = children[-1].get("children")
                if isinstance(last_children, list):
                    last_children.append(data)
                    return
            children.append({"type": "paragraph", "children": [data]})
            return
        children.append(data)

    def visit_Text(self, node: nodes.Text) -> None:
        """Append a text leaf to the current frame's children, if it has any."""
        self.append_node({"type": "text", "value": node.astext()})

    def depart_Text(self, node: nodes.Text) -> None:
        """No-op: text leaves have no closing handler."""

    def visit_doctest_block(self, node: nodes.Element) -> None:
        """Treat a docutils ``doctest_block`` as a python literal block.

        ``>>>``-style examples in NumPy / Google docstrings parse to a
        :class:`docutils.nodes.doctest_block`, which we map onto our
        ``literalBlock`` shape with ``language="python"`` so the renderer
        applies the python syntax-highlighting class.

        Raises
        ------
        docutils.nodes.SkipNode
            Always: ``doctest_block`` is a fixed-text element captured via
            :meth:`docutils.nodes.Element.astext` on visit.
        """
        if not self._stack:
            raise nodes.SkipNode
        data = self._stack[-1]["data"]
        children = data.get("children")
        if isinstance(children, list):
            children.append(
                {
                    "type": "literalBlock",
                    "language": "python",
                    "code": node.astext(),
                },
            )
        raise nodes.SkipNode

    def visit_classifier(self, node: nodes.Element) -> None:
        """Skip the ``classifier`` (type annotation) subtree.

        docutils emits ``classifier`` for type annotations between
        ``term`` and ``definition`` in a definition_list_item:

            project : str
                Sphinx project name.

        For the spike we drop the classifier entirely; the type
        information for autodoc parameters lives in
        :attr:`Symbol.parameters` and the doctree-side classifier is
        derivative.

        Raises
        ------
        docutils.nodes.SkipNode
            Always: skip both children and depart.
        """
        raise nodes.SkipNode

    # ─── autodoc desc handling ─────────────────────────────────────────────
    #
    # ``addnodes.desc`` is the autodoc container for one symbol. It contains
    # one or more ``desc_signature`` (the rendered signature) followed by
    # exactly one ``desc_content`` (the docstring body). The translator
    # converts the whole subtree into a :class:`Symbol` record stored in the
    # builder-level ``SymbolAccumulator`` and leaves a ``symbolRef``
    # placeholder in the doctree at the ``desc``'s position.

    def visit_desc(self, node: nodes.Element) -> None:
        """Open a ``desc`` frame to accumulate one Symbol's payload.

        Raises
        ------
        docutils.nodes.SkipNode
            When there is no parent block frame to attach the placeholder to;
            a stray ``desc`` outside any section is skipped silently.
        """
        if not self._stack:
            raise nodes.SkipNode
        objtype = node.get("objtype", "") or ""
        kind = normalize_symbol_kind(objtype)
        self._stack.append(
            {
                "kind": "desc",
                "data": {
                    "id": "",
                    "kind": kind,
                    "name": "",
                    "qualname": "",
                    "module": "",
                    "signature": "",
                    "parameters": [],
                    "returns": None,
                    "docstring_summary": "",
                    "docstring_body": [],
                    "source": None,
                },
            },
        )

    def depart_desc(self, node: nodes.Element) -> None:
        """Close the ``desc``; record the Symbol and emit a placeholder.

        On exit:

        - If the accumulated record has an ``id``, validate it as a
          :class:`Symbol` and append to the builder-scoped accumulator.
        - Append a ``symbolRef`` placeholder node to the parent block frame
          (typically a section's ``children``) so the doctree retains the
          symbol's position without inlining its content.
        """
        frame = self._stack.pop()
        symbol_data = frame["data"]
        symbol_id = symbol_data["id"]
        if symbol_id and self._symbol_accumulator is not None:
            self._symbol_accumulator.append(Symbol.model_validate(symbol_data))
        if symbol_id and self._stack:
            self._stack[-1]["data"]["children"].append(
                {"type": "symbolRef", "symbolId": symbol_id},
            )

    def _resolve_source(
        self,
        module_name: str,
        fullname: str,
    ) -> dict[str, t.Any] | None:
        """Look up a Python object's source file for ``Symbol.source``.

        Reads the repo URL from ``conf.py``'s ``source_repository``
        (gp-sphinx convention) and the source root from the optional
        ``astro_source_root`` (defaults to ``app.srcdir.parent`` —
        i.e. the docs dir's parent, which is the workspace root for
        the canonical ``docs/`` layout). Returns ``None`` whenever any
        prerequisite is missing so missing config gracefully degrades
        to ``Symbol.source = null``.
        """
        if self._builder is None:
            return None
        config = getattr(self._builder.app, "config", None)
        if config is None:
            return None
        repo_url = getattr(config, "source_repository", "") or ""
        if repo_url == "":
            return None
        explicit_root = getattr(config, "astro_source_root", None)
        if explicit_root is not None:
            source_root = pathlib.Path(str(explicit_root))
        else:
            source_root = pathlib.Path(self._builder.app.srcdir).parent
        return _resolve_symbol_source(
            module_name=module_name,
            fullname=fullname,
            repo_url=str(repo_url),
            source_root=source_root,
        )

    def visit_desc_signature(self, node: nodes.Element) -> None:
        """Capture signature metadata into the surrounding ``desc`` frame.

        Raises
        ------
        docutils.nodes.SkipNode
            Always: the signature's children (desc_addname, desc_name,
            desc_parameterlist, …) carry inline-text fragments that the
            existing visitors would happily emit into the parent's children
            list. Skipping the subtree avoids that leakage.
        """
        if self._stack and self._stack[-1]["kind"] == "desc":
            sym = self._stack[-1]["data"]
            ids = node.get("ids") or []
            if ids:
                sym["id"] = ids[0]
            sym["module"] = node.get("module", "") or ""
            fullname = node.get("fullname", "") or ""
            sym["qualname"] = fullname
            sym["name"] = fullname.rsplit(".", 1)[-1] if fullname else ""
            sym["source"] = self._resolve_source(sym["module"], fullname)
            # Capture only the parameter list (already wrapped in
            # ``(...)`` by ``addnodes.desc_parameterlist.astext``) and the
            # optional return annotation (already prefixed with ``" -> "``
            # by ``addnodes.desc_returns.astext``). Calling ``astext()``
            # on the entire ``desc_signature`` would re-include the
            # qualified name (already in ``module`` / ``qualname``) and
            # the inline ``objtype`` badge that ``sphinx-autodoc-api-style``
            # injects into the signature subtree.
            parts: list[str] = []
            for plist in node.findall(addnodes.desc_parameterlist):
                parts.append(plist.astext())
                break
            for returns in node.findall(addnodes.desc_returns):
                parts.append(returns.astext())
                break
            sym["signature"] = "".join(parts)
        raise nodes.SkipNode

    def visit_desc_content(self, node: nodes.Element) -> None:
        """Open a fake block-container frame for the docstring body."""
        self._stack.append({"kind": "desc_content", "data": {"children": []}})

    def depart_desc_content(self, node: nodes.Element) -> None:
        """Move accumulated block children into the parent ``desc`` frame."""
        frame = self._stack.pop()
        body: list[dict[str, t.Any]] = frame["data"]["children"]
        if not (self._stack and self._stack[-1]["kind"] == "desc"):
            return
        sym = self._stack[-1]["data"]
        sym["docstring_body"] = body
        if not body:
            return
        first_block = body[0]
        if first_block.get("type") != "paragraph":
            return
        sym["docstring_summary"] = "".join(
            child.get("value", "")
            for child in first_block.get("children", [])
            if child.get("type") == "text"
        )
