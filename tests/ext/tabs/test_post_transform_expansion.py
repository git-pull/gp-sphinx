"""Tests for the expansion pass of :class:`TabsPostTransform`.

Start from a pre-built :class:`TabSetNode` / :class:`TabItemNode` tree
and run the expansion pass in isolation; assert the resulting
``[TabInputNode, TabLabelNode, panel]`` triples and the selection rules.
"""

from __future__ import annotations

import typing as t

import pytest
from docutils import frontend, nodes, utils
from docutils.parsers.rst import Parser

from sphinx_ux_tabs import _transforms
from sphinx_ux_tabs._css import SUT
from sphinx_ux_tabs._nodes import (
    TabInputNode,
    TabItemNode,
    TabLabelNode,
    TabSetNode,
)
from sphinx_ux_tabs._transforms import _expand_tab_sets, _resolve_selected_index


def _make_document() -> nodes.document:
    settings = frontend.OptionParser(components=(Parser,)).get_default_values()
    return utils.new_document("<test>", settings)


def _make_tab_item(
    label_text: str,
    body_text: str,
    *,
    selected: bool = False,
    sync_id: str = "",
) -> TabItemNode:
    """Build a TabItemNode carrying a label + panel body child."""
    item = TabItemNode(selected=selected, sync_id=sync_id)
    item += nodes.label("", label_text)
    panel = nodes.container("", is_div=True)
    panel += nodes.paragraph("", body_text)
    item += panel
    return item


def _make_tab_set(*items: TabItemNode) -> TabSetNode:
    """Wrap ``items`` in a TabSetNode."""
    tab_set = TabSetNode()
    for item in items:
        tab_set += item
    return tab_set


def test_expansion_emits_input_label_panel_triple_per_item() -> None:
    """One TabInputNode + one TabLabelNode + one panel per source TabItemNode."""
    doc = _make_document()
    tab_set = _make_tab_set(
        _make_tab_item("Python", "py body"),
        _make_tab_item("Rust", "rs body"),
        _make_tab_item("Go", "go body"),
    )
    doc += tab_set
    _expand_tab_sets(doc)

    children = list(tab_set.children)
    # 3 tabs × 3 children = 9.
    assert len(children) == 9
    for triple_index in range(3):
        triple = children[triple_index * 3 : triple_index * 3 + 3]
        assert isinstance(triple[0], TabInputNode)
        assert isinstance(triple[1], TabLabelNode)
        assert isinstance(triple[2], nodes.container)


def test_expansion_first_input_is_checked_when_no_selection() -> None:
    """Index ``0`` is checked when no item carries ``:selected:``."""
    doc = _make_document()
    tab_set = _make_tab_set(
        _make_tab_item("A", "a"),
        _make_tab_item("B", "b"),
    )
    doc += tab_set
    _expand_tab_sets(doc)

    inputs = [c for c in tab_set.children if isinstance(c, TabInputNode)]
    checked = [i for i in inputs if i["checked"]]
    assert len(checked) == 1
    assert checked[0] is inputs[0]


def test_expansion_explicit_selected_overrides_index_zero() -> None:
    """An explicit ``selected=True`` overrides the default first-tab choice."""
    doc = _make_document()
    tab_set = _make_tab_set(
        _make_tab_item("A", "a"),
        _make_tab_item("B", "b", selected=True),
        _make_tab_item("C", "c"),
    )
    doc += tab_set
    _expand_tab_sets(doc)

    inputs = [c for c in tab_set.children if isinstance(c, TabInputNode)]
    assert inputs[0]["checked"] is False
    assert inputs[1]["checked"] is True
    assert inputs[2]["checked"] is False


def test_expansion_multiple_selected_emits_warning_first_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multiple ``selected`` items emit a warning; the first one wins."""
    captured: list[str] = []

    def fake_warning(message: str, *args: t.Any, **_kwargs: t.Any) -> None:
        captured.append(message % args if args else message)

    monkeypatch.setattr(_transforms._LOGGER, "warning", fake_warning)

    items = [
        TabItemNode(selected=False),
        TabItemNode(selected=True),
        TabItemNode(selected=True),
    ]
    chosen = _resolve_selected_index(items)
    assert chosen == 1
    assert any("multiple selected" in msg.lower() for msg in captured)


def test_expansion_input_ids_match_label_for_attr() -> None:
    """Each TabLabelNode's ``input_id`` matches the preceding input's ``input_id``."""
    doc = _make_document()
    tab_set = _make_tab_set(
        _make_tab_item("A", "a"),
        _make_tab_item("B", "b"),
    )
    doc += tab_set
    _expand_tab_sets(doc)

    children = list(tab_set.children)
    for index in range(2):
        input_node = children[index * 3]
        label_node = children[index * 3 + 1]
        assert isinstance(input_node, TabInputNode)
        assert isinstance(label_node, TabLabelNode)
        assert label_node["input_id"] == input_node["input_id"]


def test_expansion_set_names_shared_within_a_set_distinct_across_sets() -> None:
    """All radios in a set share one ``name``; different sets use different names."""
    doc = _make_document()
    set_a = _make_tab_set(_make_tab_item("A", "a"), _make_tab_item("B", "b"))
    set_b = _make_tab_set(_make_tab_item("C", "c"), _make_tab_item("D", "d"))
    doc += set_a
    doc += set_b
    _expand_tab_sets(doc)

    names_a = {c["set_name"] for c in set_a.children if isinstance(c, TabInputNode)}
    names_b = {c["set_name"] for c in set_b.children if isinstance(c, TabInputNode)}
    assert len(names_a) == 1
    assert len(names_b) == 1
    assert names_a != names_b
    assert next(iter(names_a)) == SUT.set_name(0)
    assert next(iter(names_b)) == SUT.set_name(1)


def test_expansion_panel_carries_namespace_class() -> None:
    """The expanded panel container picks up the ``gp-sphinx-tabs__panel`` class."""
    doc = _make_document()
    tab_set = _make_tab_set(_make_tab_item("A", "a"))
    doc += tab_set
    _expand_tab_sets(doc)

    panels = [
        c
        for c in tab_set.children
        if isinstance(c, nodes.container)
        and not isinstance(c, (TabInputNode, TabLabelNode))
    ]
    assert len(panels) == 1
    assert SUT.PANEL in panels[0]["classes"]


def test_expansion_label_preserves_inline_children() -> None:
    """Inline markup inside the source label survives onto the TabLabelNode."""
    doc = _make_document()
    item = TabItemNode()
    label = nodes.label("", "")
    label += nodes.literal("Python", "Python")
    item += label
    panel = nodes.container("", is_div=True)
    panel += nodes.paragraph("", "body")
    item += panel
    tab_set = _make_tab_set(item)
    doc += tab_set
    _expand_tab_sets(doc)

    labels = [c for c in tab_set.children if isinstance(c, TabLabelNode)]
    assert len(labels) == 1
    assert any(isinstance(c, nodes.literal) for c in labels[0].children)


def test_expansion_carries_sync_id_onto_label() -> None:
    """``sync_id`` on the source TabItemNode is copied onto the TabLabelNode."""
    doc = _make_document()
    tab_set = _make_tab_set(
        _make_tab_item("Bash", "echo hi", sync_id="bash"),
    )
    doc += tab_set
    _expand_tab_sets(doc)

    labels = [c for c in tab_set.children if isinstance(c, TabLabelNode)]
    assert len(labels) == 1
    assert labels[0]["sync_id"] == "bash"


def test_expansion_carries_sync_group_onto_label() -> None:
    """``sync_group`` on each source TabItemNode lands on the TabLabelNode."""
    doc = _make_document()
    item_a = _make_tab_item("Bash", "echo hi", sync_id="bash")
    item_b = _make_tab_item("Zsh", "print -P %~", sync_id="zsh")
    # Simulate what TabSetDirective does once it resolves :sync-group:.
    item_a["sync_group"] = "shell"
    item_b["sync_group"] = "shell"
    tab_set = _make_tab_set(item_a, item_b)
    doc += tab_set
    _expand_tab_sets(doc)

    labels = [c for c in tab_set.children if isinstance(c, TabLabelNode)]
    assert len(labels) == 2
    assert labels[0]["sync_group"] == "shell"
    assert labels[1]["sync_group"] == "shell"


def test_expansion_propagates_label_ids_for_cross_references() -> None:
    """``ids``/``names`` registered on the source label survive expansion.

    The ``:name:`` option on a ``tab-item`` directive calls
    ``self.add_name(label)`` which populates ``label["ids"]`` and
    ``label["names"]``.  The expansion pass must copy those onto the
    emitted :class:`TabLabelNode` so ``{ref}`` resolution lands on a
    real anchor in the final HTML.
    """
    doc = _make_document()
    item = TabItemNode()
    label = nodes.label("", "Python")
    label["ids"] = ["my-tab"]
    label["names"] = ["my-tab"]
    item += label
    panel = nodes.container("", is_div=True)
    panel += nodes.paragraph("", "body")
    item += panel
    tab_set = _make_tab_set(item)
    doc += tab_set
    _expand_tab_sets(doc)

    labels = [c for c in tab_set.children if isinstance(c, TabLabelNode)]
    assert len(labels) == 1
    assert labels[0]["ids"] == ["my-tab"]
    assert labels[0]["names"] == ["my-tab"]
