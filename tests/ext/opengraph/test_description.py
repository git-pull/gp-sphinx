"""Tests for gp_opengraph._description.

Build small doctrees via docutils and feed them into ``DescriptionParser``,
asserting the visitor extracts the expected prose and honors length caps.
"""

from __future__ import annotations

from docutils.frontend import OptionParser
from docutils.parsers.rst import Parser as RstParser
from docutils.utils import new_document

from gp_opengraph._description import get_description


def _parse_rst(source: str):  # type: ignore[no-untyped-def]
    """Return a fully-parsed docutils document for ``source``."""
    parser = RstParser()
    settings = OptionParser(components=(RstParser,)).get_default_values()
    document = new_document("<test>", settings)
    parser.parse(source, document)
    return document


def test_first_paragraph_wins() -> None:
    """A plain paragraph is returned verbatim (below the length cap)."""
    doctree = _parse_rst("Hello world, this is a description.\n")
    result = get_description(doctree, description_length=200)
    assert "Hello world" in result
    assert "description" in result


def test_title_is_skipped_when_known() -> None:
    """A title matching known_titles is excluded from the description."""
    src = "My Page Title\n=============\n\nBody paragraph with content.\n"
    doctree = _parse_rst(src)
    result = get_description(doctree, 200, known_titles={"My Page Title"})
    assert "Body paragraph" in result
    assert "My Page Title" not in result


def test_admonition_is_skipped() -> None:
    """Admonition bodies are excluded from the description."""
    src = (
        "Intro paragraph.\n\n"
        ".. note::\n\n   This note should not appear.\n\n"
        "Outro paragraph.\n"
    )
    doctree = _parse_rst(src)
    result = get_description(doctree, 200)
    assert "Intro paragraph" in result
    assert "Outro paragraph" in result
    assert "This note should not appear" not in result


def test_code_block_is_skipped() -> None:
    """Literal-block text is not included."""
    src = (
        "Before code.\n\n"
        ".. code-block:: python\n\n"
        "   import secret_value\n\n"
        "After code.\n"
    )
    doctree = _parse_rst(src)
    result = get_description(doctree, 200)
    assert "Before code" in result
    assert "After code" in result
    assert "secret_value" not in result


def test_truncation_adds_ellipsis() -> None:
    """Descriptions longer than desc_len are cut and gain '...' trailer."""
    long_text = "word " * 100
    doctree = _parse_rst(long_text + "\n")
    result = get_description(doctree, description_length=30)
    assert len(result) <= 30
    assert result.endswith("...")


def test_short_cap_below_three_has_no_ellipsis() -> None:
    """A description_length below 3 truncates without adding '...'."""
    doctree = _parse_rst("abcdefghij\n")
    result = get_description(doctree, description_length=2)
    assert len(result) <= 2
    assert "..." not in result
