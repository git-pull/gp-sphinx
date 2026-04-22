"""Detect a pre-existing ``<meta name="description">`` in collected meta tags.

Ported verbatim from ``sphinxext.opengraph._meta_parser`` (v0.13.0), with
a narrowed return type annotation (upstream declared ``bool`` but actually
returns ``str | bool | None``).

Examples
--------
>>> from sphinx_gp_opengraph._meta import get_meta_description
>>> get_meta_description('<meta name="description" content="hello">')
'hello'
>>> get_meta_description('<meta name="other" content="hi">') is None
True
"""

from __future__ import annotations

import html.parser


def get_meta_description(meta_tags: str) -> str | bool | None:
    """Return the ``content`` of an existing description meta tag, if any.

    Parameters
    ----------
    meta_tags : str
        Concatenated ``<meta ...>`` tags (as produced by Sphinx).

    Returns
    -------
    str | bool | None
        The content string when a matching meta tag carries a ``content``
        attribute; ``True`` when a description tag is present but has no
        content attribute; ``None`` otherwise.
    """
    htp = HTMLTextParser()
    htp.feed(meta_tags)
    htp.close()

    return htp.meta_description


class HTMLTextParser(html.parser.HTMLParser):
    """Flag the presence (and content) of a ``<meta name="description">``."""

    def __init__(self) -> None:
        super().__init__()
        self.meta_description: str | bool | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Capture the description content when the matching meta opens."""
        # For example:
        # attrs = [("content", "My manual description"), ("name", "description")]
        if ("name", "description") in attrs:
            self.meta_description = True
            for name, value in attrs:
                if name == "content":
                    self.meta_description = value
                    break
