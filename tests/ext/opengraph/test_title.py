"""Tests for sphinx_gp_opengraph._title.get_title."""

from __future__ import annotations

from sphinx_gp_opengraph._title import get_title


def test_plain_text_title_round_trips() -> None:
    """A title with no HTML returns identical text and outside-text."""
    all_text, outside = get_title("libtmux-mcp")
    assert all_text == "libtmux-mcp"
    assert outside == "libtmux-mcp"


def test_tags_are_stripped_from_all_text() -> None:
    """all_text flattens the full title; outside drops tagged spans."""
    all_text, outside = get_title("<em>libtmux</em>-mcp")
    assert all_text == "libtmux-mcp"
    assert outside == "-mcp"


def test_nested_tags_nest_the_level_counter() -> None:
    """Nested tags keep outside-text empty until every tag closes."""
    all_text, outside = get_title("<span><em>inner</em></span>")
    assert all_text == "inner"
    assert outside == ""


def test_empty_title() -> None:
    """Empty input returns empty strings."""
    assert get_title("") == ("", "")


def test_get_title_with_void_elements() -> None:
    """Void elements like <br> and <img> do not permanently increase the nesting level."""
    title, text_outside_tags = get_title("text<br>more text<img src='test.png'>final")
    assert title == "textmore textfinal"
    assert text_outside_tags == "textmore textfinal"


def test_get_title_with_xhtml_self_closing_void_elements() -> None:
    """XHTML self-closing void tags (e.g. <br/>) keep level balanced.

    ``HTMLParser`` routes ``<br/>`` through ``handle_startendtag``, whose
    default fires both ``handle_starttag`` AND ``handle_endtag``. Filtering
    only the start path would leave the unbalanced end decrement, sending
    ``self.level`` negative and dropping every subsequent chunk from
    ``text_outside_tags``.
    """
    all_text, outside = get_title("before<br/>after")
    assert all_text == "beforeafter"
    assert outside == "beforeafter"

    all_text, outside = get_title("a<img src='x'/>b<hr/>c")
    assert all_text == "abc"
    assert outside == "abc"
