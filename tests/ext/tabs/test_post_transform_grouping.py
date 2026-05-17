"""Tests for the grouping pass of :class:`TabsPostTransform`.

Construct synthetic doctrees of :class:`TabContainer` siblings and run
the grouping pass directly, then assert the rewritten tree shape.

Style A NamedTuple parametrization (see CLAUDE.md Testing Strategy).
"""

from __future__ import annotations

import typing as t

import pytest
from docutils import frontend, nodes, utils
from docutils.parsers.rst import Parser

from sphinx_ux_tabs._nodes import (
    TabContainer,
    TabItemNode,
    TabSetNode,
)
from sphinx_ux_tabs._transforms import _group_tab_containers


def _make_document() -> nodes.document:
    """Return a fresh empty document for tree building."""
    settings = frontend.OptionParser(components=(Parser,)).get_default_values()
    return utils.new_document("<test>", settings)


def _make_tab_container(
    label_text: str,
    body_text: str,
    *,
    new_set: bool = False,
    selected: bool = False,
) -> TabContainer:
    """Build a TabContainer carrying a label + a body-content child."""
    container = TabContainer(new_set=new_set, selected=selected)
    container += nodes.label("", label_text)
    body = nodes.container("", is_div=True)
    body += nodes.paragraph("", body_text)
    container += body
    return container


def _make_paragraph(text: str) -> nodes.paragraph:
    """Build a plain paragraph used as a tab-run breaker."""
    return nodes.paragraph("", text)


class _GroupingFixture(t.NamedTuple):
    """Test case for the grouping pass."""

    test_id: str
    inputs: tuple[t.Callable[[], nodes.Node], ...]
    expected_sets: int
    expected_items_per_set: tuple[int, ...]


def _three_consecutive_inputs() -> tuple[t.Callable[[], nodes.Node], ...]:
    return (
        lambda: _make_tab_container("A", "alpha"),
        lambda: _make_tab_container("B", "bravo"),
        lambda: _make_tab_container("C", "charlie"),
    )


def _two_runs_split_by_paragraph() -> tuple[t.Callable[[], nodes.Node], ...]:
    return (
        lambda: _make_tab_container("A", "alpha"),
        lambda: _make_tab_container("B", "bravo"),
        lambda: _make_paragraph("breaker"),
        lambda: _make_tab_container("C", "charlie"),
        lambda: _make_tab_container("D", "delta"),
    )


def _new_set_break_mid_run() -> tuple[t.Callable[[], nodes.Node], ...]:
    return (
        lambda: _make_tab_container("A", "alpha"),
        lambda: _make_tab_container("B", "bravo"),
        lambda: _make_tab_container("C", "charlie", new_set=True),
        lambda: _make_tab_container("D", "delta"),
    )


def _single_container() -> tuple[t.Callable[[], nodes.Node], ...]:
    return (lambda: _make_tab_container("solo", "lone tab"),)


_GROUPING_FIXTURES: list[_GroupingFixture] = [
    _GroupingFixture(
        test_id="three-consecutive",
        inputs=_three_consecutive_inputs(),
        expected_sets=1,
        expected_items_per_set=(3,),
    ),
    _GroupingFixture(
        test_id="two-runs-paragraph-break",
        inputs=_two_runs_split_by_paragraph(),
        expected_sets=2,
        expected_items_per_set=(2, 2),
    ),
    _GroupingFixture(
        test_id="new-set-break",
        inputs=_new_set_break_mid_run(),
        expected_sets=2,
        expected_items_per_set=(2, 2),
    ),
    _GroupingFixture(
        test_id="single-container",
        inputs=_single_container(),
        expected_sets=1,
        expected_items_per_set=(1,),
    ),
]


@pytest.mark.parametrize(
    list(_GroupingFixture._fields),
    _GROUPING_FIXTURES,
    ids=[f.test_id for f in _GROUPING_FIXTURES],
)
def test_grouping_pass(
    test_id: str,
    inputs: tuple[t.Callable[[], nodes.Node], ...],
    expected_sets: int,
    expected_items_per_set: tuple[int, ...],
) -> None:
    """The grouping pass folds consecutive TabContainer siblings."""
    del test_id
    doc = _make_document()
    for factory in inputs:
        doc += factory()
    _group_tab_containers(doc)

    tab_sets = [c for c in doc.children if isinstance(c, TabSetNode)]
    assert len(tab_sets) == expected_sets
    actual_counts = tuple(
        sum(1 for child in ts.children if isinstance(child, TabItemNode))
        for ts in tab_sets
    )
    assert actual_counts == expected_items_per_set


def test_grouping_leaves_paragraph_in_place() -> None:
    """A paragraph between two tab runs survives as a sibling of the sets."""
    doc = _make_document()
    doc += _make_tab_container("A", "alpha")
    doc += _make_paragraph("breaker")
    doc += _make_tab_container("B", "bravo")
    _group_tab_containers(doc)

    # Expect: [TabSetNode(A), paragraph, TabSetNode(B)]
    assert len(doc.children) == 3
    assert isinstance(doc.children[0], TabSetNode)
    assert isinstance(doc.children[1], nodes.paragraph)
    assert isinstance(doc.children[2], TabSetNode)


def test_grouping_clears_original_tab_containers() -> None:
    """No TabContainer survives the grouping pass."""
    doc = _make_document()
    doc += _make_tab_container("A", "alpha")
    doc += _make_tab_container("B", "bravo")
    _group_tab_containers(doc)

    surviving = list(doc.findall(TabContainer))
    assert surviving == []


def test_grouping_preserves_tab_label_and_panel_per_item() -> None:
    """Each TabItemNode keeps the original ``[label, panel]`` children."""
    doc = _make_document()
    doc += _make_tab_container("Python", "py body")
    doc += _make_tab_container("Rust", "rs body")
    _group_tab_containers(doc)

    tab_set = doc.children[0]
    assert isinstance(tab_set, TabSetNode)
    items = [c for c in tab_set.children if isinstance(c, TabItemNode)]
    assert len(items) == 2
    for item in items:
        assert len(item.children) == 2
        # First child is the label, second the container body.
        assert isinstance(item.children[0], nodes.label)
        assert isinstance(item.children[1], nodes.container)


def test_grouping_handles_nested_runs() -> None:
    """A TabContainer whose panel contains another run still groups inner run."""
    doc = _make_document()
    outer = _make_tab_container("Outer-A", "")
    # The outer panel (children[1]) is a container body — drop two TabContainers in.
    outer_body = outer.children[1]
    assert isinstance(outer_body, nodes.Element)
    inner1 = _make_tab_container("Inner-A", "ia")
    inner2 = _make_tab_container("Inner-B", "ib")
    outer_body += inner1
    outer_body += inner2
    doc += outer

    _group_tab_containers(doc)

    # The outer is rewritten into its own TabSetNode at the top level.
    top_sets = [c for c in doc.children if isinstance(c, TabSetNode)]
    assert len(top_sets) == 1

    # The TabItem holding the rewritten "Outer-A" has, somewhere inside it,
    # a TabSetNode wrapping the two inner items.
    item = top_sets[0].children[0]
    assert isinstance(item, TabItemNode)
    inner_sets = list(item.findall(TabSetNode))
    assert len(inner_sets) == 1
    inner_items = [n for n in inner_sets[0].children if isinstance(n, TabItemNode)]
    assert len(inner_items) == 2
