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

from gp_sphinx_astro_builder.models import Document

if t.TYPE_CHECKING:
    from sphinx.builders import Builder


_FrameKind = t.Literal[
    "section",
    "title",
    "paragraph",
    "emphasis",
    "strong",
    "literal",
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
    ) -> None:
        super().__init__(document)
        self._builder = builder
        if not docname and builder is not None:
            docname = getattr(builder, "current_docname", "") or ""
        self._docname = docname
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

    def visit_Text(self, node: nodes.Text) -> None:
        """Append a text leaf to the current frame's children."""
        text_value = node.astext()
        if not self._stack:
            return
        self._stack[-1]["data"]["children"].append(
            {"type": "text", "value": text_value},
        )

    def depart_Text(self, node: nodes.Text) -> None:
        """No-op: text leaves have no closing handler."""
