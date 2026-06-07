"""Synthetic docutils components for live component-autodoc demos.

Grows one demo class per component type so the
``docs/packages/sphinx-autodoc-docutils`` examples page can exercise
every ``auto*`` directive against realistic metadata.

Examples
--------
>>> DemoReorderTransform.default_priority
760
"""

from __future__ import annotations

import typing as t

from docutils import nodes
from docutils.parsers import Parser
from docutils.readers import standalone
from docutils.transforms import Transform
from docutils.writers import Writer

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata


class DemoReorderTransform(Transform):
    """Move demo-badge paragraphs ahead of their sibling paragraphs.

    Runs late in the read phase (priority 760) so it sees the fully
    parsed document but still precedes reference resolution.
    """

    default_priority = 760

    def apply(self) -> None:
        """Hoist each ``demo-badge`` paragraph to the front of its parent."""
        for paragraph in tuple(self.document.findall(nodes.paragraph)):
            if "demo-badge" in paragraph.get("classes", ()):
                parent = paragraph.parent
                parent.remove(paragraph)
                parent.insert(0, paragraph)


class DemoArticleReader(standalone.Reader):  # type: ignore[type-arg]
    """Read standalone article sources with the demo transform applied.

    Extends the stock standalone reader's transform set with
    :class:`DemoReorderTransform` so demo badges surface first.
    """

    supported = ("demo-article",)
    config_section = "demo article reader"

    def get_transforms(self) -> list[type[Transform]]:
        """Return the standalone transforms plus the demo reorderer."""
        return [*super().get_transforms(), DemoReorderTransform]


class DemoLineParser(Parser):
    """Parse line-oriented demo sources into one paragraph per line."""

    supported = ("demo-lines", "demolines")
    config_section = "demo line parser"

    def parse(self, inputstring: str, document: nodes.document) -> None:
        """Append one paragraph node per non-empty input line."""
        self.setup_parse(inputstring, document)
        for line in inputstring.splitlines():
            if line.strip():
                document += nodes.paragraph(text=line.strip())
        self.finish_parse()


class demo_marker(nodes.General, nodes.Inline, nodes.Element):
    """Inline marker node rendered as a highlighted ``<mark>`` span."""


def visit_demo_marker(translator: nodes.NodeVisitor, node: demo_marker) -> None:
    """Open the ``<mark>`` wrapper for a demo marker node."""
    translator.body.append("<mark>")  # type: ignore[attr-defined]


def depart_demo_marker(translator: nodes.NodeVisitor, node: demo_marker) -> None:
    """Close the ``<mark>`` wrapper for a demo marker node."""
    translator.body.append("</mark>")  # type: ignore[attr-defined]


class DemoTextTranslator(nodes.NodeVisitor):
    """Translate paragraphs into plain text lines for the demo writer."""

    def __init__(self, document: nodes.document) -> None:
        super().__init__(document)
        self.lines: list[str] = []

    def visit_paragraph(self, node: nodes.paragraph) -> None:
        """Open a fresh output line."""
        self.lines.append("")

    def depart_paragraph(self, node: nodes.paragraph) -> None:
        """Close the current output line."""

    def visit_Text(self, node: nodes.Text) -> None:
        """Append literal text to the current line."""
        if self.lines:
            self.lines[-1] += node.astext()

    def unknown_visit(self, node: nodes.Node) -> None:
        """Ignore nodes the demo writer does not understand."""

    def unknown_departure(self, node: nodes.Node) -> None:
        """Ignore nodes the demo writer does not understand."""


class DemoPlainWriter(Writer):  # type: ignore[type-arg]
    """Write documents as plain text lines, one paragraph per line.

    Assigns ``translator_class`` in ``__init__`` (the django-docutils
    style) rather than as a class attribute, which exercises the
    defensive resolution the ``autowriter`` directive performs.
    """

    supported = ("demo-plain",)
    config_section = "demo plain writer"

    def __init__(self) -> None:
        super().__init__()
        self.translator_class = DemoTextTranslator

    def translate(self) -> None:
        """Visit the document and join the collected lines."""
        document = self.document
        if document is None:
            self.output = ""
            return
        visitor = DemoTextTranslator(document)
        document.walkabout(visitor)
        self.output = "\n".join(visitor.lines)


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the demo components with Sphinx.

    Examples
    --------
    >>> class FakeApp:
    ...     def __init__(self) -> None:
    ...         self.calls: list[tuple[str, object]] = []
    ...     def add_transform(self, cls: object) -> None:
    ...         self.calls.append(("add_transform", cls))
    ...     def add_source_parser(self, cls: object) -> None:
    ...         self.calls.append(("add_source_parser", cls))
    ...     def add_node(self, cls: object, **kwargs: object) -> None:
    ...         self.calls.append(("add_node", cls))
    >>> fake = FakeApp()
    >>> metadata = setup(fake)  # type: ignore[arg-type]
    >>> ("add_transform", DemoReorderTransform) in fake.calls
    True
    >>> ("add_source_parser", DemoLineParser) in fake.calls
    True
    >>> ("add_node", demo_marker) in fake.calls
    True
    >>> metadata["parallel_read_safe"]
    True
    """
    app.add_transform(DemoReorderTransform)
    app.add_source_parser(DemoLineParser)
    app.add_node(demo_marker, html=(visit_demo_marker, depart_demo_marker))
    return {
        "version": "0.0.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
