"""Extract a plain-text description from a Sphinx doctree.

``get_description`` walks a resolved doctree and returns the first chunk of
prose that Sphinx would render as the page's visible body, suitable for
inclusion in an ``og:description`` meta tag. Admonitions, code blocks, and
invisible nodes are skipped; nested lists are flattened into comma-joined
text; the result is truncated to ``description_length`` characters with a
trailing ellipsis.

Ported verbatim from ``sphinxext.opengraph._description_parser`` (v0.13.0).

Examples
--------
>>> from sphinx_gp_opengraph._description import get_description, DescriptionParser
>>> callable(get_description)
True
>>> issubclass(DescriptionParser, object)
True
"""

from __future__ import annotations

import string
import typing as t

from docutils import nodes

if t.TYPE_CHECKING:
    from collections.abc import Set


def get_description(
    doctree: nodes.document,
    description_length: int,
    known_titles: Set[str] = frozenset(),
) -> str:
    """Return a plain-text description extracted from ``doctree``.

    Parameters
    ----------
    doctree : docutils.nodes.document
        Resolved Sphinx doctree for one page.
    description_length : int
        Maximum number of characters to return.
    known_titles : collections.abc.Set[str]
        Titles to treat as the page title (skipped from the description).

    Returns
    -------
    str
        Flattened, HTML-escaped description, truncated to
        ``description_length`` with a trailing ``...`` when truncated.
    """
    mcv = DescriptionParser(
        doctree,
        desc_len=description_length,
        known_titles=known_titles,
    )
    doctree.walkabout(mcv)
    return mcv.description


class DescriptionParser(nodes.NodeVisitor):
    """Walk a doctree and accumulate a text description.

    Skips admonitions, invisible nodes, raw blocks, and literal blocks.
    Titles are separated by colons; list elements by commas; sequential
    lists by periods.

    Parameters
    ----------
    document : docutils.nodes.document
        The document being walked.
    desc_len : int
        Maximum character count for the resulting description.
    known_titles : collections.abc.Set[str]
        Titles treated as the page title; the first such title encountered
        is skipped.
    """

    def __init__(
        self,
        document: nodes.document,
        *,
        desc_len: int,
        known_titles: Set[str] = frozenset(),
    ) -> None:
        super().__init__(document)
        self.description = ""
        self.desc_len = desc_len
        self.list_level = 0
        self.known_titles = known_titles
        self.first_title_found = False

        # Exceptions can't be raised from dispatch_departure()
        # This is used to loop the stop call back to the next dispatch_visit()
        self.stop = False

    def dispatch_visit(self, node: nodes.Node) -> None:
        """Accumulate text from ``node`` unless it should be skipped."""
        if self.stop:
            raise nodes.StopTraversal

        # Skip comments & all admonitions
        if isinstance(node, (nodes.Admonition, nodes.Invisible)):
            raise nodes.SkipNode

        # Mark start of nested lists
        if isinstance(node, nodes.Sequential):
            self.list_level += 1
            if self.list_level > 1:
                self.description += "-"

        # Skip the first title if it's the title of the page
        if not self.first_title_found and isinstance(node, nodes.title):
            self.first_title_found = True
            if node.astext() in self.known_titles:
                raise nodes.SkipNode

        if isinstance(node, nodes.raw) or isinstance(node.parent, nodes.literal_block):
            raise nodes.SkipNode

        # Only include leaf nodes in the description
        if len(node.children) == 0:
            text = node.astext().replace("\r", "").replace("\n", " ").strip()

            # HTML escaping happens once at the boundary in _make_tag; doing
            # it here too would double-escape (``&`` → ``&amp;`` →
            # ``&amp;amp;``).

            # Remove double spaces
            while text.find("  ") != -1:
                text = text.replace("  ", " ")

            # Put a space between elements if one does not already exist.
            if (
                len(self.description) > 0
                and len(text) > 0
                and self.description[-1] not in string.whitespace
                and text[0] not in string.whitespace + string.punctuation
            ):
                self.description += " "

            self.description += text

    def dispatch_departure(self, node: nodes.Node) -> None:
        """Emit separators and enforce the length cap when leaving nodes."""
        # Separate title from text
        if isinstance(node, nodes.title):
            self.description += ":"

        # Separate list elements
        if isinstance(node, nodes.Part):
            self.description += ","

        # Separate end of list from text
        if isinstance(node, nodes.Sequential):
            if self.description and self.description[-1] == ",":
                self.description = self.description[:-1]
            self.description += "."
            self.list_level -= 1

        # Check for length
        if len(self.description) > self.desc_len:
            self.description = self.description[: self.desc_len]
            if self.desc_len >= 3:
                self.description = self.description[:-3] + "..."

            self.stop = True
