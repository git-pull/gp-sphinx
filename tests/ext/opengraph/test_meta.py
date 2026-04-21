"""Tests for gp_opengraph._meta.get_meta_description."""

from __future__ import annotations

from gp_opengraph._meta import get_meta_description


def test_detects_description_with_content() -> None:
    """Returns the content attribute value when present."""
    tags = '<meta name="description" content="hello world">'
    assert get_meta_description(tags) == "hello world"


def test_description_without_content_returns_true() -> None:
    """A description meta tag without content still signals presence."""
    tags = '<meta name="description">'
    assert get_meta_description(tags) is True


def test_no_description_returns_none() -> None:
    """Tags that lack a description meta return None."""
    tags = '<meta name="keywords" content="x">'
    assert get_meta_description(tags) is None


def test_handles_multiple_tags_and_picks_description() -> None:
    """Other meta tags are ignored; the description content is returned."""
    tags = (
        '<meta name="viewport" content="width=device-width">'
        '<meta name="description" content="real content">'
        '<meta property="og:title" content="og">'
    )
    assert get_meta_description(tags) == "real content"
