"""Tests for shared signature-slot helpers."""

from __future__ import annotations

from docutils import nodes
from sphinx import addnodes

from sphinx_ux_autodoc_layout import inject_signature_slots, is_viewcode_ref


def _make_viewcode_ref() -> nodes.reference:
    source = nodes.inline(classes=["viewcode-link"])
    source += nodes.Text("[source]")
    return nodes.reference("", "", source, internal=False)


def test_is_viewcode_ref_detects_viewcode_links() -> None:
    assert is_viewcode_ref(_make_viewcode_ref()) is True
    assert is_viewcode_ref(nodes.reference("", "", nodes.inline("", "demo"))) is False


def test_inject_signature_slots_moves_viewcode_into_source_slot() -> None:
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "demo")
    sig += _make_viewcode_ref()
    badge_group = nodes.inline(classes=["sab-badge-group"])
    badge_group += nodes.inline("", "function", classes=["sab-badge"])

    injected = inject_signature_slots(
        sig,
        marker_attr="demo_slots",
        badge_node=badge_group,
    )

    assert injected is True
    slots = [
        child
        for child in sig.children
        if isinstance(child, nodes.Element) and child.get("slot")
    ]
    assert [slot.get("slot") for slot in slots] == ["badges", "source-link"]
    assert not any(is_viewcode_ref(child) for child in sig.children)


def test_inject_signature_slots_is_idempotent() -> None:
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "demo")

    first = inject_signature_slots(
        sig,
        marker_attr="demo_slots",
        badge_node=nodes.inline("", "function"),
    )
    second = inject_signature_slots(
        sig,
        marker_attr="demo_slots",
        badge_node=nodes.inline("", "function"),
    )

    assert first is True
    assert second is False
    assert (
        len(
            [
                child
                for child in sig.children
                if isinstance(child, nodes.Element) and child.get("slot")
            ]
        )
        == 1
    )


def test_inject_signature_slots_uses_explicit_source_node() -> None:
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "demo")
    explicit_source = _make_viewcode_ref()

    inject_signature_slots(
        sig,
        marker_attr="demo_slots",
        badge_node=nodes.inline("", "function"),
        source_node=explicit_source,
        extract_source_link=False,
    )

    source_slot = next(
        child
        for child in sig.children
        if isinstance(child, nodes.Element) and child.get("slot") == "source-link"
    )
    assert source_slot.children == [explicit_source]
