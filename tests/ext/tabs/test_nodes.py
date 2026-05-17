"""Pure docutils-node tests for sphinx_ux_tabs._nodes.

The five custom node types each have a small construction contract;
these tests assert their subclass relationships, default attribute
values, and that the bundled CSS class names land on every instance.
"""

from __future__ import annotations

import typing as t

import pytest
from docutils import nodes

from sphinx_ux_tabs._css import SUT
from sphinx_ux_tabs._nodes import (
    TabContainer,
    TabInputNode,
    TabItemNode,
    TabLabelNode,
    TabSetNode,
)


def test_tab_container_subclasses_container() -> None:
    """TabContainer inherits from ``nodes.container``."""
    assert issubclass(TabContainer, nodes.container)


def test_tab_set_node_subclasses_container() -> None:
    """TabSetNode inherits from ``nodes.container``."""
    assert issubclass(TabSetNode, nodes.container)


def test_tab_item_node_subclasses_container() -> None:
    """TabItemNode inherits from ``nodes.container``."""
    assert issubclass(TabItemNode, nodes.container)


def test_tab_input_node_subclasses_element() -> None:
    """TabInputNode inherits from ``nodes.Element`` (void)."""
    assert issubclass(TabInputNode, nodes.Element)


def test_tab_label_node_subclasses_text_element() -> None:
    """TabLabelNode inherits from ``nodes.TextElement``."""
    assert issubclass(TabLabelNode, nodes.TextElement)


def test_tab_container_default_attributes() -> None:
    """A bare TabContainer has ``new_set=False`` and ``selected=False``."""
    tc = TabContainer()
    assert tc["new_set"] is False
    assert tc["selected"] is False
    assert tc["is_div"] is True


def test_tab_container_carries_new_set_flag() -> None:
    """``new_set=True`` propagates onto the node attributes."""
    tc = TabContainer(new_set=True)
    assert tc["new_set"] is True


def test_tab_container_carries_selected_flag() -> None:
    """``selected=True`` propagates onto the node attributes."""
    tc = TabContainer(selected=True)
    assert tc["selected"] is True


def test_tab_set_node_carries_namespace_class() -> None:
    """TabSetNode always carries ``gp-sphinx-tabs`` in its classes."""
    ts = TabSetNode()
    assert SUT.TABS in ts["classes"]
    assert ts["is_div"] is True


def test_tab_set_node_extra_classes_appended() -> None:
    """Caller-supplied classes survive alongside the namespace class."""
    ts = TabSetNode(classes=["extra-one", "extra-two"])
    assert SUT.TABS in ts["classes"]
    assert "extra-one" in ts["classes"]
    assert "extra-two" in ts["classes"]


def test_tab_set_node_extra_classes_dedup() -> None:
    """The namespace class is not duplicated when also passed as ``classes``."""
    ts = TabSetNode(classes=[SUT.TABS, "extra-one"])
    assert ts["classes"].count(SUT.TABS) == 1


def test_tab_item_node_defaults() -> None:
    """A bare TabItemNode has ``selected=False`` and empty ``sync_id``."""
    ti = TabItemNode()
    assert ti["selected"] is False
    assert ti["sync_id"] == ""


def test_tab_item_node_carries_selected_and_sync() -> None:
    """``selected`` and ``sync_id`` survive onto the node attributes."""
    ti = TabItemNode(selected=True, sync_id="lang")
    assert ti["selected"] is True
    assert ti["sync_id"] == "lang"


def test_tab_input_node_carries_input_id_and_set_name() -> None:
    """TabInputNode carries ``input_id`` and ``set_name`` attributes."""
    inp = TabInputNode(input_id="set0-input-0", set_name="set0")
    assert inp["input_id"] == "set0-input-0"
    assert inp["set_name"] == "set0"
    assert inp["checked"] is False


def test_tab_input_node_checked_flag() -> None:
    """``checked=True`` propagates onto the node attributes."""
    inp = TabInputNode(input_id="x", set_name="s", checked=True)
    assert inp["checked"] is True


def test_tab_input_node_namespace_class_present() -> None:
    """TabInputNode always carries ``gp-sphinx-tabs__input`` in its classes."""
    inp = TabInputNode(input_id="x", set_name="s")
    assert SUT.INPUT in inp["classes"]


def test_tab_label_node_carries_text_and_for_attr() -> None:
    """TabLabelNode renders its label text and exposes ``input_id``."""
    lbl = TabLabelNode("", "Python", input_id="x")
    assert lbl.astext() == "Python"
    assert lbl["input_id"] == "x"


def test_tab_label_node_namespace_class_present() -> None:
    """TabLabelNode always carries ``gp-sphinx-tabs__label`` in its classes."""
    lbl = TabLabelNode("", "Python", input_id="x")
    assert SUT.LABEL in lbl["classes"]


def test_tab_label_node_carries_sync_id() -> None:
    """``sync_id`` propagates onto the node attributes."""
    lbl = TabLabelNode("", "Python", input_id="x", sync_id="lang")
    assert lbl["sync_id"] == "lang"


class _NamespaceFixture(t.NamedTuple):
    """Test case for the SUT id-builder helpers."""

    test_id: str
    set_index: int
    item_index: int
    expected_input_id: str
    expected_set_name: str


_NAMESPACE_FIXTURES: list[_NamespaceFixture] = [
    _NamespaceFixture(
        test_id="zeroth",
        set_index=0,
        item_index=0,
        expected_input_id="gp-sphinx-tab-set-0-input-0",
        expected_set_name="gp-sphinx-tab-set-0",
    ),
    _NamespaceFixture(
        test_id="set-one-item-two",
        set_index=1,
        item_index=2,
        expected_input_id="gp-sphinx-tab-set-1-input-2",
        expected_set_name="gp-sphinx-tab-set-1",
    ),
    _NamespaceFixture(
        test_id="larger-indices",
        set_index=12,
        item_index=4,
        expected_input_id="gp-sphinx-tab-set-12-input-4",
        expected_set_name="gp-sphinx-tab-set-12",
    ),
]


@pytest.mark.parametrize(
    list(_NamespaceFixture._fields),
    _NAMESPACE_FIXTURES,
    ids=[f.test_id for f in _NAMESPACE_FIXTURES],
)
def test_sut_id_builders_round_trip(
    test_id: str,
    set_index: int,
    item_index: int,
    expected_input_id: str,
    expected_set_name: str,
) -> None:
    """SUT id-builder helpers emit stable, namespaced ids."""
    del test_id
    assert SUT.input_id(set_index, item_index) == expected_input_id
    assert SUT.set_name(set_index) == expected_set_name
