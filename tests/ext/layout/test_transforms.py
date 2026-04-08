"""Tests for sphinx_autodoc_layout._transforms."""

from __future__ import annotations

import typing as t

from docutils import nodes
from sphinx import addnodes
from sphinx_autodoc_layout._nodes import (
    api_component,
    api_inline_component,
    api_permalink,
    gal_fold,
    gal_sig_fold,
)
from sphinx_autodoc_layout._transforms import (
    _classify_child,
    _count_field_entries,
    _fold_large_field_regions,
    _nest_python_members,
    _rebuild_signature_layout,
    _wrap_content_runs,
)


def _make_desc(
    *content_children: nodes.Node,
    domain: str = "py",
    objtype: str = "function",
    ids: tuple[str, ...] = (),
) -> addnodes.desc:
    desc = addnodes.desc(domain=domain, objtype=objtype)
    signature = addnodes.desc_signature(ids=list(ids))
    desc += signature
    content = addnodes.desc_content()
    for child in content_children:
        content += child
    desc += content
    return desc


def _make_field_list(num_fields: int = 5) -> nodes.field_list:
    fl = nodes.field_list()
    for i in range(num_fields):
        field = nodes.field()
        field += nodes.field_name("", f"param{i}")
        field += nodes.field_body("", nodes.paragraph("", f"desc {i}"))
        fl += field
    return fl


def _make_sphinx_field_list(num_params: int) -> nodes.field_list:
    fl = nodes.field_list()
    field = nodes.field()
    field += nodes.field_name("", "Parameters")
    body = nodes.field_body()
    bullets = nodes.bullet_list()
    for i in range(num_params):
        bullets += nodes.list_item("", nodes.paragraph("", f"param{i}"))
    body += bullets
    field += body
    fl += field
    return fl


def _make_parameter_list(num_params: int = 2) -> addnodes.desc_parameterlist:
    plist = addnodes.desc_parameterlist()
    for i in range(num_params):
        plist += addnodes.desc_parameter("", f"param{i}")
    return plist


def _make_toolbar() -> nodes.inline:
    toolbar = nodes.inline(classes=["gas-toolbar"])
    badge_group = nodes.inline(classes=["gas-badge-group"])
    badge_group += nodes.inline("", "method", classes=["gas-badge"])
    source_span = nodes.inline(classes=["viewcode-link"])
    source_span += nodes.Text("[source]")
    source_ref = nodes.reference("", "", source_span, internal=False)
    toolbar += badge_group
    toolbar += source_ref
    return toolbar


def _child_component_names(node: nodes.Element) -> list[str]:
    return [
        child.get("name")
        for child in node.children
        if isinstance(child, (api_component, api_inline_component))
    ]


def test_classify_paragraph_as_narrative() -> None:
    assert _classify_child(nodes.paragraph()) == "narrative"


def test_classify_field_list_as_fields() -> None:
    assert _classify_child(nodes.field_list()) == "fields"


def test_classify_desc_as_members() -> None:
    assert _classify_child(addnodes.desc()) == "members"


def test_classify_note_as_narrative() -> None:
    assert _classify_child(nodes.note()) == "narrative"


def test_wrap_groups_narrative() -> None:
    desc = _make_desc(
        nodes.paragraph("", "hello"),
        nodes.paragraph("", "world"),
    )
    _wrap_content_runs(desc)

    content = desc.children[-1]
    assert isinstance(content, addnodes.desc_content)
    assert _child_component_names(content) == ["api-description"]
    section = content.children[0]
    assert isinstance(section, api_component)
    assert "gal-region" in section.get("classes", [])
    assert len(section.children) == 2


def test_wrap_groups_contiguous_types() -> None:
    desc = _make_desc(
        nodes.paragraph("", "text"),
        _make_field_list(3),
        addnodes.desc(domain="py", objtype="method"),
    )
    _wrap_content_runs(desc)

    content = desc.children[-1]
    assert isinstance(content, addnodes.desc_content)
    assert _child_component_names(content) == [
        "api-description",
        "api-parameters",
        "api-footer",
    ]


def test_wrap_preserves_order() -> None:
    desc = _make_desc(
        nodes.paragraph("", "intro"),
        _make_field_list(2),
        nodes.paragraph("", "examples"),
        addnodes.desc(domain="py", objtype="method"),
    )
    _wrap_content_runs(desc)

    content = desc.children[-1]
    assert isinstance(content, addnodes.desc_content)
    assert _child_component_names(content) == [
        "api-description",
        "api-parameters",
        "api-description",
        "api-footer",
    ]


def test_wrap_empty_content_noop() -> None:
    desc = _make_desc()
    _wrap_content_runs(desc)
    content = desc.children[-1]
    assert isinstance(content, addnodes.desc_content)
    assert content.get("classes") == ["api-content"]
    assert len(content.children) == 0


def test_wrap_non_python_noop() -> None:
    desc = _make_desc(
        nodes.paragraph("", "text"),
        domain="cpp",
        objtype="function",
    )
    _wrap_content_runs(desc)
    content = desc.children[-1]
    assert isinstance(content, addnodes.desc_content)
    assert _child_component_names(content) == ["api-description"]


def test_nest_python_members_moves_siblings_into_class_content() -> None:
    section = nodes.section()
    class_desc = _make_desc(objtype="class", ids=("demo.LayoutDemo",))
    method_desc = _make_desc(objtype="method", ids=("demo.LayoutDemo.connect",))
    foreign_desc = _make_desc(objtype="method", ids=("demo.Other.call",))

    section += class_desc
    section += method_desc
    section += foreign_desc

    _nest_python_members(section)

    assert list(section.children) == [class_desc, foreign_desc]
    class_content = class_desc.children[-1]
    assert isinstance(class_content, addnodes.desc_content)
    assert list(class_content.children) == [method_desc]


def test_count_individual_fields() -> None:
    fl = _make_field_list(5)
    assert _count_field_entries(fl) == 5


def test_count_collapsed_bullet_list() -> None:
    fl = _make_sphinx_field_list(13)
    assert _count_field_entries(fl) == 13


def test_fold_wraps_large_field_list() -> None:
    content = addnodes.desc_content()
    section = api_component(name="api-parameters", tag="div")
    section["classes"] = ["api-parameters", "gal-region", "gal-region--fields"]
    section += _make_field_list(12)
    content += section

    _fold_large_field_regions(content, threshold=10)

    fold = section.children[0]
    assert isinstance(fold, gal_fold)
    assert fold.get("summary") == "Parameters (12)"
    assert isinstance(fold.children[0], nodes.field_list)


def test_fold_wraps_sphinx_collapsed_field_list() -> None:
    content = addnodes.desc_content()
    section = api_component(name="api-parameters", tag="div")
    section["classes"] = ["api-parameters", "gal-region", "gal-region--fields"]
    section += _make_sphinx_field_list(13)
    content += section

    _fold_large_field_regions(content, threshold=10)

    fold = section.children[0]
    assert isinstance(fold, gal_fold)
    assert fold.get("summary") == "Parameters (13)"


def test_fold_skips_small_field_list() -> None:
    content = addnodes.desc_content()
    section = api_component(name="api-parameters", tag="div")
    section["classes"] = ["api-parameters", "gal-region", "gal-region--fields"]
    fl = _make_field_list(5)
    section += fl
    content += section

    _fold_large_field_regions(content, threshold=10)

    assert isinstance(section.children[0], nodes.field_list)
    assert not isinstance(section.children[0], gal_fold)


def test_fold_skips_non_parameter_sections() -> None:
    content = addnodes.desc_content()
    section = api_component(name="api-description", tag="div")
    section["classes"] = ["api-description", "gal-region", "gal-region--narrative"]
    section += nodes.paragraph("", "text")
    content += section

    _fold_large_field_regions(content, threshold=1)

    assert isinstance(section.children[0], nodes.paragraph)


def test_rebuild_signature_layout_splits_toolbar_and_permalink() -> None:
    sig = addnodes.desc_signature(ids=["demo.func"])
    sig += addnodes.desc_name("", "func")
    sig += _make_parameter_list(2)
    sig += _make_toolbar()

    _rebuild_signature_layout(sig, threshold=10, include_permalink=True)

    assert len(sig.children) == 1
    layout = sig.children[0]
    assert isinstance(layout, api_component)
    assert layout.get("name") == "api-layout"

    left, right = layout.children
    assert isinstance(left, api_component)
    assert left.get("name") == "api-layout-left"
    assert isinstance(right, api_component)
    assert right.get("name") == "api-layout-right"

    signature = left.children[0]
    assert isinstance(signature, api_component)
    assert signature.get("name") == "api-signature"
    assert any(isinstance(child, api_permalink) for child in signature.children)
    assert any(
        isinstance(child, addnodes.desc_parameterlist) for child in signature.children
    )

    assert _child_component_names(right) == ["api-badge-container", "api-source-link"]


def test_rebuild_signature_layout_creates_fold_panel_for_large_signature() -> None:
    sig = addnodes.desc_signature(ids=["demo.LayoutDemo.__init__"])
    sig += addnodes.desc_name("", "__init__")
    sig += _make_parameter_list(13)
    sig += _make_toolbar()

    _rebuild_signature_layout(sig, threshold=10, include_permalink=True)

    layout = sig.children[0]
    assert isinstance(layout, api_component)
    left = layout.children[0]
    assert isinstance(left, api_component)
    assert _child_component_names(left) == ["api-signature", "api-signature-panel"]

    signature = left.children[0]
    panel = left.children[1]
    assert isinstance(signature, api_component)
    assert isinstance(panel, api_component)

    assert any(isinstance(child, gal_sig_fold) for child in signature.children)
    assert not any(
        isinstance(child, addnodes.desc_parameterlist) for child in signature.children
    )
    html_attrs = t.cast(dict[str, str], panel.get("html_attrs", {}))
    assert html_attrs.get("id") == ("demo.LayoutDemo.__init__--signature-panel")
    assert isinstance(panel.children[0], addnodes.desc_parameterlist)


def test_rebuild_signature_layout_skips_multiline_signatures() -> None:
    sig = addnodes.desc_signature(ids=["demo.func"], is_multiline=True)
    sig += addnodes.desc_signature_line()
    original = list(sig.children)

    _rebuild_signature_layout(sig, threshold=10, include_permalink=True)

    assert list(sig.children) == original
