"""Unit tests for sphinx_autodoc_typehints_gp._field_xref_transform."""

from __future__ import annotations

import typing as t

import pytest
from docutils import nodes
from sphinx import addnodes

from sphinx_autodoc_typehints_gp._field_xref_transform import (
    _is_em_dash_separator,
    _normalize_xref_contnode,
    _role_class_for_field_name,
    _wrap_prefix_in_paragraph,
)

# ---------------------------------------------------------------------------
# _role_class_for_field_name
# ---------------------------------------------------------------------------


class _RoleClassFixture(t.NamedTuple):
    test_id: str
    field_name: str
    expected: str


_ROLE_CLASS_FIXTURES: list[_RoleClassFixture] = [
    _RoleClassFixture("type_param", "type server", "py-class"),
    _RoleClassFixture("rtype", "rtype", "py-class"),
    _RoleClassFixture("ytype", "ytype", "py-class"),
    _RoleClassFixture("yieldtype", "yieldtype value", "py-class"),
    _RoleClassFixture("parameters_label", "Parameters", "py-class"),
    _RoleClassFixture("returns_label", "Returns", "py-class"),
    _RoleClassFixture("return_type_label", "Return type", "py-class"),
    _RoleClassFixture("raises_lowercase", "raises", "py-exc"),
    _RoleClassFixture("raises_label", "Raises", "py-exc"),
    _RoleClassFixture("raises_named", "raises ValueError", "py-exc"),
    _RoleClassFixture("except_named", "except OSError", "py-exc"),
    _RoleClassFixture("empty", "", "py-class"),
    _RoleClassFixture("uppercase_raises", "RAISES", "py-exc"),
]


@pytest.mark.parametrize(
    list(_RoleClassFixture._fields),
    _ROLE_CLASS_FIXTURES,
    ids=[f.test_id for f in _ROLE_CLASS_FIXTURES],
)
def test_role_class_picks_per_field_name(
    test_id: str,
    field_name: str,
    expected: str,
) -> None:
    """_role_class_for_field_name maps field names to xref role classes."""
    del test_id
    assert _role_class_for_field_name(field_name) == expected


# ---------------------------------------------------------------------------
# _is_em_dash_separator
# ---------------------------------------------------------------------------


class _DashFixture(t.NamedTuple):
    test_id: str
    text: str
    expected: bool


_EN_DASH = chr(0x2013)

_DASH_FIXTURES: list[_DashFixture] = [
    _DashFixture("plain_en_dash", f" {_EN_DASH} ", True),
    _DashFixture("en_dash_then_text", f" {_EN_DASH} desc", True),
    _DashFixture("ascii_double_hyphen", " -- description", True),
    _DashFixture("colon_marker", "item: ", False),
    _DashFixture("plain_text", "Description text", False),
    _DashFixture("single_hyphen_isnt_separator", " - text", False),
    _DashFixture("empty", "", False),
]


@pytest.mark.parametrize(
    list(_DashFixture._fields),
    _DASH_FIXTURES,
    ids=[f.test_id for f in _DASH_FIXTURES],
)
def test_is_em_dash_separator(
    test_id: str,
    text: str,
    expected: bool,
) -> None:
    """_is_em_dash_separator detects Sphinx's prefix/description boundary."""
    del test_id
    assert _is_em_dash_separator(text) is expected


# ---------------------------------------------------------------------------
# _normalize_xref_contnode (docutils-tree unit, no Sphinx app)
# ---------------------------------------------------------------------------


def _make_field_with_xref(
    field_name: str,
    contnode: nodes.Node,
    *,
    refdomain: str = "py",
    reftarget: str = "Foo",
) -> tuple[nodes.field, addnodes.pending_xref]:
    """Build a minimal `field/field_name + field_body/paragraph/xref` tree."""
    xref = addnodes.pending_xref(
        "",
        contnode,
        refdomain=refdomain,
        reftype="class",
        reftarget=reftarget,
    )
    paragraph = nodes.paragraph("", "", xref)
    body = nodes.field_body("", paragraph)
    field = nodes.field("", nodes.field_name("", field_name), body)
    return field, xref


def test_normalize_replaces_text_contnode_with_literal() -> None:
    """A pending_xref with a plain Text contnode gets a literal wrap."""
    _, xref = _make_field_with_xref("type x", nodes.Text("Server"))
    assert _normalize_xref_contnode(xref) is True
    assert len(xref.children) == 1
    literal = xref.children[0]
    assert isinstance(literal, nodes.literal)
    assert literal["classes"] == ["xref", "py", "py-class"]
    assert literal.astext() == "Server"
    assert xref["refspecific"] is True


def test_normalize_replaces_literal_strong_with_canonical_literal() -> None:
    """A literal_strong contnode (raises) gets replaced with py-exc literal."""
    _, xref = _make_field_with_xref(
        "raises",
        addnodes.literal_strong("OSError", "OSError"),
    )
    assert _normalize_xref_contnode(xref) is True
    literal = xref.children[0]
    assert isinstance(literal, nodes.literal)
    assert literal["classes"] == ["xref", "py", "py-exc"]
    assert literal.astext() == "OSError"


def test_normalize_replaces_literal_emphasis_with_canonical_literal() -> None:
    """A literal_emphasis contnode (param type) gets replaced with py-class."""
    _, xref = _make_field_with_xref(
        "type x",
        addnodes.literal_emphasis("int", "int"),
    )
    assert _normalize_xref_contnode(xref) is True
    literal = xref.children[0]
    assert isinstance(literal, nodes.literal)
    assert literal["classes"] == ["xref", "py", "py-class"]


def test_normalize_skips_non_python_domain() -> None:
    """A pending_xref whose refdomain is not 'py' is left alone."""
    _, xref = _make_field_with_xref(
        "type x",
        nodes.Text("X"),
        refdomain="std",
    )
    assert _normalize_xref_contnode(xref) is False
    # Original Text contnode still present
    assert isinstance(xref.children[0], nodes.Text)


def test_normalize_skips_empty_title() -> None:
    """A pending_xref whose contnode renders no text is left alone."""
    _, xref = _make_field_with_xref("type x", nodes.Text(""))
    assert _normalize_xref_contnode(xref) is False


# ---------------------------------------------------------------------------
# _wrap_prefix_in_paragraph
# ---------------------------------------------------------------------------


def test_wrap_prefix_splits_at_en_dash() -> None:
    """The wrapper captures children before the en-dash separator."""
    paragraph = nodes.paragraph(
        "",
        "",
        nodes.strong("name", "name"),
        nodes.Text(" "),
        nodes.Text(f" {_EN_DASH} description text"),
    )
    assert _wrap_prefix_in_paragraph(paragraph) is True
    assert len(paragraph.children) == 2
    wrapper = paragraph.children[0]
    assert isinstance(wrapper, nodes.inline)
    assert "gp-sphinx-field-prefix" in (wrapper.get("classes") or [])
    # Wrapper has the strong + space
    assert len(wrapper.children) == 2
    # Em-dash text remains as a sibling
    assert _EN_DASH in str(paragraph.children[1])


def test_wrap_prefix_handles_no_separator_with_identifier() -> None:
    """A no-separator field body containing an identifier gets wrapped.

    Covers ``:rtype:`` / ``:raises:`` rows whose entire content is a
    single ``pending_xref`` (the type or exception name).
    """
    xref = addnodes.pending_xref(
        "",
        nodes.Text("Pane"),
        refdomain="py",
        reftype="class",
        reftarget="Pane",
    )
    paragraph = nodes.paragraph("", "", xref)
    assert _wrap_prefix_in_paragraph(paragraph) is True
    assert len(paragraph.children) == 1
    wrapper = paragraph.children[0]
    assert isinstance(wrapper, nodes.inline)
    assert "gp-sphinx-field-prefix" in (wrapper.get("classes") or [])
    assert wrapper.astext() == "Pane"


def test_wrap_prefix_skips_returns_field() -> None:
    """The ``Returns`` field body's prose stays unwrapped.

    ``Returns`` is a prose-style field — its body holds free-form
    description text rather than a typed parameter / identifier
    prefix. Wrapping it would re-style ordinary body copy to
    monospace and clash with embedded ``:any:`None```-style inline
    code spans inside the prose.
    """
    paragraph = nodes.paragraph(
        "",
        "",
        nodes.Text("Formatted result with "),
        nodes.literal("", "None"),
        nodes.Text(" embedded."),
    )
    assert _wrap_prefix_in_paragraph(paragraph, field_name="Returns") is False
    # Children unchanged
    assert len(paragraph.children) == 3


def test_wrap_prefix_skips_yields_and_notes() -> None:
    """Other prose-style fields (Yields, Notes) are also skipped."""
    for field_name in ("Yields", "Notes", "Examples", "Warning"):
        paragraph = nodes.paragraph("", "", nodes.Text("description text"))
        assert _wrap_prefix_in_paragraph(paragraph, field_name=field_name) is False


def test_wrap_prefix_applies_for_return_type_field() -> None:
    """``Return type`` is NOT prose — it gets wrapped despite no separator."""
    xref = addnodes.pending_xref(
        "",
        nodes.Text("Pane"),
        refdomain="py",
        reftype="class",
        reftarget="Pane",
    )
    paragraph = nodes.paragraph("", "", xref)
    assert _wrap_prefix_in_paragraph(paragraph, field_name="Return type") is True


def test_wrap_prefix_idempotent() -> None:
    """A paragraph already containing the wrapper is not re-wrapped."""
    inner = nodes.inline(
        "",
        "",
        nodes.Text("Pane"),
        classes=["gp-sphinx-field-prefix"],
    )
    paragraph = nodes.paragraph("", "", inner)
    assert _wrap_prefix_in_paragraph(paragraph) is False
    # Single wrapper, not nested
    assert len(paragraph.children) == 1


def test_wrap_prefix_skips_empty_paragraph() -> None:
    """A paragraph with no children returns False without mutating."""
    paragraph = nodes.paragraph()
    assert _wrap_prefix_in_paragraph(paragraph) is False
