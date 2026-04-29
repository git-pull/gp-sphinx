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

import typing as t

from docutils import nodes

from gp_sphinx_astro_builder.models import Document, Symbol
from gp_sphinx_astro_builder.symbols import normalize_symbol_kind

if t.TYPE_CHECKING:
    from sphinx.builders import Builder

    from gp_sphinx_astro_builder.symbols import SymbolAccumulator


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
        self._stack[-1]["data"]["children"].append(frame["data"])

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
        self._stack[-1]["data"]["children"].append(frame["data"])

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
        self._stack[-1]["data"]["children"].append(frame["data"])

    def visit_reference(self, node: nodes.Element) -> None:
        """Open a reference frame, normalising refuri / refid into one href."""
        refuri = node.get("refuri")
        refid = node.get("refid")
        if refuri:
            href = refuri
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
        """Close the reference and attach it to the parent inline collector."""
        frame = self._stack.pop()
        self._stack[-1]["data"]["children"].append(frame["data"])

    def visit_image(self, node: nodes.Element) -> None:
        """Append an image leaf node to the current inline collector.

        Raises
        ------
        docutils.nodes.SkipNode
            Always: ``image`` is a leaf in docutils — there are no children
            to traverse and no closing handler is needed.
        """
        if self._stack:
            self._stack[-1]["data"]["children"].append(
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

    def visit_Text(self, node: nodes.Text) -> None:
        """Append a text leaf to the current frame's children, if it has any.

        Some frame shapes (the ``desc`` frame for autodoc symbols, the
        ``definitionListItem`` frame with its term/definition slots) do not
        have a flat ``children`` list. Text that lands inside one of those
        frames belongs to a sub-section the translator hasn't pushed a
        proper frame for yet (e.g., a stray ``classifier`` between
        ``term`` and ``definition``), so we drop it silently rather than
        crashing the build.
        """
        text_value = node.astext()
        if not self._stack:
            return
        data = self._stack[-1]["data"]
        children = data.get("children")
        if not isinstance(children, list):
            return
        children.append({"type": "text", "value": text_value})

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
            sym["signature"] = node.astext()
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
