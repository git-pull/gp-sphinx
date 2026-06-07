"""Unit tests for the shared inline fact-value helpers."""

from __future__ import annotations

import typing as t

import pytest
from docutils import nodes
from sphinx import addnodes

from sphinx_ux_autodoc_layout import build_chip_paragraph, build_linked_literal


class LinkedLiteralCase(t.NamedTuple):
    """Test case for build_linked_literal()."""

    test_id: str
    target: str
    display: str | None
    expected_text: str
    expected_explicit: bool


_LINKED_LITERAL_CASES: list[LinkedLiteralCase] = [
    LinkedLiteralCase(
        test_id="target_as_display",
        target="pkg.mod.Cls",
        display=None,
        expected_text="pkg.mod.Cls",
        expected_explicit=False,
    ),
    LinkedLiteralCase(
        test_id="bare_name_display",
        target="pkg.mod.Cls",
        display="Cls",
        expected_text="Cls",
        expected_explicit=True,
    ),
    LinkedLiteralCase(
        test_id="method_target",
        target="pkg.mod.Cls.visit_table",
        display="visit_table",
        expected_text="visit_table",
        expected_explicit=True,
    ),
]


@pytest.mark.parametrize(
    "case",
    _LINKED_LITERAL_CASES,
    ids=lambda c: c.test_id,
)
def test_build_linked_literal(case: LinkedLiteralCase) -> None:
    """build_linked_literal wraps a literal chip in a py-obj xref."""
    xref = build_linked_literal(case.target, case.display)
    assert isinstance(xref, addnodes.pending_xref)
    assert xref["refdomain"] == "py"
    assert xref["reftype"] == "obj"
    assert xref["reftarget"] == case.target
    assert xref["refwarn"] is False
    assert xref["refexplicit"] is case.expected_explicit
    assert xref.astext() == case.expected_text
    literal = xref.children[0]
    assert isinstance(literal, nodes.literal)
    assert "xref" in literal["classes"]


def test_build_linked_literal_no_refspecific() -> None:
    """Fully-qualified targets resolve in exact-match mode (searchmode 0)."""
    xref = build_linked_literal("pkg.mod.Cls")
    assert not xref.hasattr("refspecific")


class ChipParagraphCase(t.NamedTuple):
    """Test case for build_chip_paragraph()."""

    test_id: str
    items: list[str]
    expected_text: str
    expected_literals: int


_CHIP_PARAGRAPH_CASES: list[ChipParagraphCase] = [
    ChipParagraphCase(
        test_id="three_strings",
        items=["html5", "xhtml", "html"],
        expected_text="html5, xhtml, html",
        expected_literals=3,
    ),
    ChipParagraphCase(
        test_id="single_string",
        items=["standalone"],
        expected_text="standalone",
        expected_literals=1,
    ),
    ChipParagraphCase(
        test_id="empty_renders_dash",
        items=[],
        expected_text="—",
        expected_literals=1,
    ),
]


@pytest.mark.parametrize(
    "case",
    _CHIP_PARAGRAPH_CASES,
    ids=lambda c: c.test_id,
)
def test_build_chip_paragraph(case: ChipParagraphCase) -> None:
    """build_chip_paragraph renders one literal chip per item."""
    paragraph = build_chip_paragraph(list(case.items))
    assert paragraph.astext() == case.expected_text
    literal_count = sum(
        isinstance(child, nodes.literal) for child in paragraph.children
    )
    assert literal_count == case.expected_literals


def test_build_chip_paragraph_accepts_nodes() -> None:
    """Pre-built nodes (e.g. linked literals) pass through unchanged."""
    xref = build_linked_literal("pkg.Cls")
    paragraph = build_chip_paragraph([xref, "plain"])
    assert paragraph.children[0] is xref
    assert paragraph.astext() == "pkg.Cls, plain"
