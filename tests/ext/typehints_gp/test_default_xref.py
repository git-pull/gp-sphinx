"""Unit tests for sphinx_autodoc_typehints_gp._default_xref_transform."""

from __future__ import annotations

import ast
import typing as t

import pytest
from docutils import nodes
from sphinx import addnodes

from sphinx_autodoc_typehints_gp._default_xref_transform import (
    _ast_to_nodes,
    _attr_chain,
    _transform_default_value_span,
    _xref,
)

# ---------------------------------------------------------------------------
# _xref shape
# ---------------------------------------------------------------------------


def test_xref_builds_pending_xref_with_literal_contnode() -> None:
    """The pending_xref wraps a `:py:obj:`-styled literal.

    `obj` is the Python domain's catch-all reftype — it resolves
    classes, module-level data, functions, and attributes uniformly.
    Restricting to `class` would leave data-attribute targets like
    libtmux's `DEFAULT_OPTION_SCOPE` silently unlinked.
    """
    n = _xref("mod.Foo", "Foo")
    assert n["refdomain"] == "py"
    assert n["reftype"] == "obj"
    assert n["reftarget"] == "mod.Foo"
    assert isinstance(n.children[0], nodes.literal)
    literal = n.children[0]
    assert literal["classes"] == ["xref", "py", "py-obj"]
    assert literal.astext() == "Foo"


# ---------------------------------------------------------------------------
# _attr_chain
# ---------------------------------------------------------------------------


class _AttrChainFixture(t.NamedTuple):
    test_id: str
    source: str
    expected: str | None


_ATTR_CHAIN_FIXTURES: list[_AttrChainFixture] = [
    _AttrChainFixture("two_parts", "a.b", "a.b"),
    _AttrChainFixture("three_parts", "a.b.c", "a.b.c"),
    _AttrChainFixture("call_base", "a().b", None),
]


@pytest.mark.parametrize(
    list(_AttrChainFixture._fields),
    _ATTR_CHAIN_FIXTURES,
    ids=[f.test_id for f in _ATTR_CHAIN_FIXTURES],
)
def test_attr_chain_dot_joins_static_chains_only(
    test_id: str,
    source: str,
    expected: str | None,
) -> None:
    """_attr_chain reduces dotted chains anchored at a Name."""
    del test_id
    tree = ast.parse(source, mode="eval")
    attr = tree.body
    assert isinstance(attr, ast.Attribute)
    assert _attr_chain(attr) == expected


# ---------------------------------------------------------------------------
# _ast_to_nodes shapes
# ---------------------------------------------------------------------------


class _AstShapeFixture(t.NamedTuple):
    test_id: str
    source: str
    xref_targets: list[str]


_AST_SHAPE_FIXTURES: list[_AstShapeFixture] = [
    _AstShapeFixture("bare_name", "Foo", ["Foo"]),
    _AstShapeFixture("attribute", "mod.Foo", ["mod.Foo"]),
    _AstShapeFixture("nested_attribute", "a.b.Foo", ["a.b.Foo"]),
    _AstShapeFixture("tuple_of_one", "(Foo,)", ["Foo"]),
    _AstShapeFixture("tuple_of_two", "(Foo, Bar)", ["Foo", "Bar"]),
    _AstShapeFixture("list_of_classes", "[Foo, Bar]", ["Foo", "Bar"]),
    _AstShapeFixture("call_no_args", "Foo()", ["Foo"]),
    _AstShapeFixture("call_with_kw", "Foo(x=Bar)", ["Foo", "Bar"]),
    _AstShapeFixture("constant_int", "42", []),
    _AstShapeFixture("constant_str", "'hello'", []),
    _AstShapeFixture("constant_none", "None", []),  # ast.Constant — no xref
    _AstShapeFixture("ellipsis", "...", []),
]


@pytest.mark.parametrize(
    list(_AstShapeFixture._fields),
    _AST_SHAPE_FIXTURES,
    ids=[f.test_id for f in _AST_SHAPE_FIXTURES],
)
def test_ast_to_nodes_emits_expected_xref_targets(
    test_id: str,
    source: str,
    xref_targets: list[str],
) -> None:
    """_ast_to_nodes emits one pending_xref per identifier reference."""
    del test_id
    tree = ast.parse(source, mode="eval")
    out = _ast_to_nodes(tree.body)
    actual = [n["reftarget"] for n in out if isinstance(n, addnodes.pending_xref)]
    assert actual == xref_targets


def test_ast_to_nodes_raises_on_lambda() -> None:
    """Lambdas are unsupported and raise SyntaxError so the caller falls back."""
    tree = ast.parse("lambda: 1", mode="eval")
    with pytest.raises(SyntaxError):
        _ast_to_nodes(tree.body)


def test_ast_to_nodes_raises_on_dict_literal() -> None:
    """Dict literals are unsupported (deferred to a future resolver)."""
    tree = ast.parse("{'a': 1}", mode="eval")
    with pytest.raises(SyntaxError):
        _ast_to_nodes(tree.body)


# ---------------------------------------------------------------------------
# _transform_default_value_span
# ---------------------------------------------------------------------------


def _make_default_value_span(text: str) -> nodes.inline:
    return nodes.inline("", text, classes=["default_value"])


def test_transform_rewrites_identifier_to_xref() -> None:
    """A bare identifier becomes a pending_xref with the right target."""
    span = _make_default_value_span("Foo")
    assert _transform_default_value_span(span) is True
    xrefs = list(span.findall(addnodes.pending_xref))
    assert len(xrefs) == 1
    assert xrefs[0]["reftarget"] == "Foo"


def test_transform_rewrites_tuple_of_classes() -> None:
    """A tuple-of-classes default produces one xref per class."""
    span = _make_default_value_span("(Foo, Bar)")
    assert _transform_default_value_span(span) is True
    xrefs = list(span.findall(addnodes.pending_xref))
    assert [n["reftarget"] for n in xrefs] == ["Foo", "Bar"]


def test_transform_tuple_branch_propagates_env_to_elements() -> None:
    """Tuple-element xrefs honour the ``env`` documentation gate.

    Regression for the bug where the ``ast.Tuple`` arm of
    ``_ast_to_nodes`` forgot to forward ``env=env`` into
    ``_wrap_seq``. Without the forward, ``_is_documented`` was bypassed
    for tuple elements and undocumented targets emitted misleading
    ``<code class="xref py py-obj">`` styling without an ``<a>``
    wrapper. With ``env`` carrying an empty ``objects`` table every
    target is "undocumented", so each tuple element should fall back
    to a plain ``nodes.Text`` rather than a ``pending_xref``.
    """
    import types

    span = _make_default_value_span("(Foo, Bar)")
    env = t.cast(
        "t.Any",
        types.SimpleNamespace(domaindata={"py": {"objects": {}}}),
    )
    assert _transform_default_value_span(span, env=env) is True
    xrefs = list(span.findall(addnodes.pending_xref))
    assert xrefs == []
    # Both element names survive as plain text inside the span.
    plain = span.astext()
    assert "Foo" in plain
    assert "Bar" in plain


def test_transform_leaves_unsupported_text_alone() -> None:
    """Unparseable text leaves the span untouched."""
    span = _make_default_value_span("lambda: 1")
    assert _transform_default_value_span(span) is False
    # Still has the original text content
    assert span.astext() == "lambda: 1"


def test_transform_skips_empty_span() -> None:
    """Whitespace-only spans are ignored."""
    span = _make_default_value_span("   ")
    assert _transform_default_value_span(span) is False
