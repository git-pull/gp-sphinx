"""Tests for sphinx_ux_autodoc_layout._nodes."""

from __future__ import annotations

from docutils import nodes

from sphinx_ux_autodoc_layout._nodes import (
    api_component,
    api_fold,
    api_inline_component,
    api_permalink,
    api_region,
    api_sig_fold,
    api_slot,
    build_api_component,
    build_api_inline_component,
    build_api_slot,
)


def test_gal_region_is_general_element() -> None:
    r = api_region(kind="narrative")
    assert isinstance(r, nodes.General)
    assert isinstance(r, nodes.Element)


def test_gal_region_stores_kind() -> None:
    r = api_region(kind="fields")
    assert r.get("kind") == "fields"


def test_gal_fold_is_general_element() -> None:
    f = api_fold(kind="parameters", summary="Parameters (5)")
    assert isinstance(f, nodes.General)
    assert isinstance(f, nodes.Element)


def test_gal_fold_stores_attributes() -> None:
    f = api_fold(kind="parameters", summary="Parameters (5)", open=True)
    assert f.get("kind") == "parameters"
    assert f.get("summary") == "Parameters (5)"
    assert f.get("open") is True


def test_gal_fold_default_open_is_falsy() -> None:
    f = api_fold(kind="parameters", summary="P (1)")
    assert not f.get("open")


def test_api_component_stores_name_and_tag() -> None:
    node = api_component(name="api-layout", tag="div")
    assert node.get("name") == "api-layout"
    assert node.get("tag") == "div"


def test_build_api_component_adds_classes() -> None:
    node = build_api_component("api-layout", classes=("legacy",))
    assert node.get("classes") == ["api-layout", "legacy"]


def test_api_permalink_stores_href() -> None:
    link = api_permalink(href="#demo.func", title="Link to this definition")
    assert link.get("href") == "#demo.func"
    assert link.get("title") == "Link to this definition"


def test_api_inline_component_stores_name_and_tag() -> None:
    node = api_inline_component(name="api-source-link", tag="span")
    assert node.get("name") == "api-source-link"
    assert node.get("tag") == "span"


def test_build_api_inline_component_adds_classes() -> None:
    node = build_api_inline_component("api-source-link", classes=("legacy",))
    assert node.get("classes") == ["api-source-link", "legacy"]


def test_api_slot_stores_slot_name() -> None:
    slot = api_slot(slot="badges")
    assert slot.get("slot") == "badges"


def test_build_api_slot_adds_slot_classes() -> None:
    slot = build_api_slot("source-link", nodes.inline("", "[source]"))
    assert slot.get("classes") == ["api-slot", "api-slot--source-link"]
    assert slot.astext() == "[source]"


def test_gal_sig_fold_stores_panel_id() -> None:
    fold = api_sig_fold(first_param="host", param_count=13, panel_id="sig-panel")
    assert fold.get("first_param") == "host"
    assert fold.get("param_count") == 13
    assert fold.get("panel_id") == "sig-panel"
