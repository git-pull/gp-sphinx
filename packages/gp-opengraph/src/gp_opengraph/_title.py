"""Extract plain text from an HTML-formatted Sphinx title.

Ported verbatim from ``sphinxext.opengraph._title_parser`` (v0.13.0).

Examples
--------
>>> from gp_opengraph._title import get_title
>>> get_title("<em>libtmux</em>-mcp")
('libtmux-mcp', '-mcp')
"""

from __future__ import annotations

import html.parser


def get_title(title: str) -> tuple[str, str]:
    """Return ``(all_text, text_outside_tags)`` parsed from a title string.

    Parameters
    ----------
    title : str
        Title text that may contain HTML markup (e.g. an ``<em>`` span
        added by a Sphinx transform).

    Returns
    -------
    tuple[str, str]
        Full text (tags stripped) and the subset that appeared outside
        any HTML tag. The second element is used when a title has been
        decorated with visual affordances (icons, wrappers) that should
        be stripped for search-engine metadata.
    """
    htp = HTMLTextParser()
    htp.feed(title)
    htp.close()

    return htp.text, htp.text_outside_tags


class HTMLTextParser(html.parser.HTMLParser):
    """Track text-inside-tags vs text-outside-tags while parsing HTML."""

    def __init__(self) -> None:
        super().__init__()
        # All text found
        self.text = ""
        # Only text outside of html tags
        self.text_outside_tags = ""
        self.level = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Increase the tag-nesting level."""
        self.level += 1

    def handle_endtag(self, tag: str) -> None:
        """Decrease the tag-nesting level."""
        self.level -= 1

    def handle_data(self, data: str) -> None:
        """Accumulate text, tracking whether it fell outside any tag."""
        self.text += data
        if self.level == 0:
            self.text_outside_tags += data
