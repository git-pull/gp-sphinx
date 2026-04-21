"""Tests for gp_opengraph._title.get_title."""

from __future__ import annotations

from gp_opengraph._title import get_title


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
