"""Tests for sphinx_autodoc_layout._transforms."""

from __future__ import annotations

import types
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
    on_doctree_resolved,
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


def _make_parameter(
    name: str,
    *,
    annotation: str | None = None,
    default: str | None = None,
) -> addnodes.desc_parameter:
    param = addnodes.desc_parameter()
    param += addnodes.desc_sig_name("", name)
    if annotation is not None:
        type_name = addnodes.desc_sig_name("", "", nodes.emphasis("", annotation))
        param += addnodes.desc_sig_punctuation("", ":")
        param += addnodes.desc_sig_space("", " ")
        param += type_name
    if default is not None:
        if annotation is not None:
            param += addnodes.desc_sig_space("", " ")
        param += addnodes.desc_sig_operator("", "=")
        if annotation is not None:
            param += addnodes.desc_sig_space("", " ")
        param += nodes.inline("", default, classes=["default_value"])
    return param


def _make_parameter_list(
    num_params: int = 2,
    *,
    annotation: str | None = None,
) -> addnodes.desc_parameterlist:
    plist = addnodes.desc_parameterlist()
    for i in range(num_params):
        plist += _make_parameter(f"param{i}", annotation=annotation)
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


def _make_typed_parameters_field_list(types: dict[str, str]) -> nodes.field_list:
    fl = nodes.field_list()
    field = nodes.field()
    field += nodes.field_name("", "Parameters")
    body = nodes.field_body()
    bullets = nodes.bullet_list()
    for name, type_name in types.items():
        paragraph = nodes.paragraph()
        paragraph += addnodes.literal_strong("", name)
        paragraph += nodes.Text(" (")
        paragraph += nodes.emphasis("", type_name)
        paragraph += nodes.Text(")")
        bullets += nodes.list_item("", paragraph)
    body += bullets
    field += body
    fl += field
    return fl


def _find_component(node: nodes.Element, name: str) -> api_component:
    for child in node.children:
        if isinstance(child, api_component) and child.get("name") == name:
            return child
    raise AssertionError(f"component not found: {name}")


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


def test_wrap_places_nested_members_in_api_footer() -> None:
    section = nodes.section()
    class_desc = _make_desc(
        nodes.paragraph("", "intro"),
        objtype="class",
        ids=("demo.LayoutDemo",),
    )
    method_desc = _make_desc(objtype="method", ids=("demo.LayoutDemo.connect",))
    section += class_desc
    section += method_desc

    _nest_python_members(section)
    _wrap_content_runs(class_desc)

    class_content = class_desc.children[-1]
    assert isinstance(class_content, addnodes.desc_content)
    assert _child_component_names(class_content) == [
        "api-description",
        "api-footer",
    ]
    footer = class_content.children[1]
    assert isinstance(footer, api_component)
    assert footer.get("name") == "api-footer"
    assert list(footer.children) == [method_desc]


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
    desc = _make_desc(ids=("demo.func",))
    sig = desc.children[0]
    assert isinstance(sig, addnodes.desc_signature)
    sig += addnodes.desc_name("", "func")
    sig += _make_parameter_list(2)
    sig += _make_toolbar()

    _rebuild_signature_layout(
        desc,
        sig,
        threshold=10,
        include_permalink=True,
        show_annotations=True,
    )

    assert len(sig.children) == 1
    layout = sig.children[0]
    assert isinstance(layout, api_component)
    assert layout.get("name") == "api-layout"
    assert layout.get("html_attrs") is None

    left, right = layout.children
    assert isinstance(left, api_component)
    assert left.get("name") == "api-layout-left"
    assert isinstance(right, api_component)
    assert right.get("name") == "api-layout-right"

    signature = left.children[0]
    assert isinstance(signature, api_component)
    assert signature.get("name") == "api-signature"
    assert isinstance(left.children[1], api_permalink)
    assert any(
        isinstance(child, addnodes.desc_parameterlist) for child in signature.children
    )

    assert _child_component_names(right) == ["api-badge-container", "api-source-link"]


def test_rebuild_signature_layout_uses_expanded_wrapper_for_large_signature() -> None:
    desc = _make_desc(ids=("demo.LayoutDemo.__init__",))
    sig = desc.children[0]
    assert isinstance(sig, addnodes.desc_signature)
    sig += addnodes.desc_name("", "__init__")
    sig += _make_parameter_list(13)
    sig += _make_toolbar()

    _rebuild_signature_layout(
        desc,
        sig,
        threshold=10,
        include_permalink=True,
        show_annotations=True,
    )

    layout = sig.children[0]
    assert isinstance(layout, api_component)
    assert layout.get("html_attrs") is None
    left = layout.children[0]
    assert isinstance(left, api_component)
    assert isinstance(left.children[0], api_component)
    assert isinstance(left.children[1], api_permalink)

    signature = left.children[0]
    assert isinstance(signature, api_component)
    assert any(isinstance(child, gal_sig_fold) for child in signature.children)
    expanded = _find_component(signature, "api-signature-expanded")
    html_attrs = t.cast(dict[str, str], expanded.get("html_attrs", {}))
    assert html_attrs.get("id") == ("demo.LayoutDemo.__init__--signature-expanded")
    plist = expanded.children[0]
    assert isinstance(plist, addnodes.desc_parameterlist)
    assert plist.get("multi_line_parameter_list") is True
    assert plist.get("multi_line_trailing_comma") is False
    collapse = expanded.children[1]
    assert isinstance(collapse, api_inline_component)
    assert collapse.get("name") == "gal-sig-collapse"
    collapse_attrs = t.cast(dict[str, str], collapse.get("html_attrs", {}))
    assert collapse_attrs.get("aria-controls") == (
        "demo.LayoutDemo.__init__--signature-expanded"
    )
    assert collapse.astext() == "[collapse]"


def test_rebuild_signature_layout_enriches_annotations_from_field_list() -> None:
    desc = _make_desc(
        _make_typed_parameters_field_list({"host": "str", "port": "int"}),
        ids=("demo.LayoutDemo.__init__",),
    )
    sig = desc.children[0]
    assert isinstance(sig, addnodes.desc_signature)
    sig += addnodes.desc_name("", "__init__")
    plist = addnodes.desc_parameterlist()
    plist += _make_parameter("host")
    plist += _make_parameter("port", default="5432")
    sig += plist

    _wrap_content_runs(desc)
    _rebuild_signature_layout(
        desc,
        sig,
        threshold=1,
        include_permalink=False,
        show_annotations=True,
    )

    layout = sig.children[0]
    assert isinstance(layout, api_component)
    left = layout.children[0]
    assert isinstance(left, api_component)
    signature = left.children[0]
    assert isinstance(signature, api_component)
    expanded = _find_component(signature, "api-signature-expanded")
    expanded_plist = expanded.children[0]
    assert isinstance(expanded_plist, addnodes.desc_parameterlist)
    params = list(expanded_plist.findall(addnodes.desc_parameter))

    assert params[0].astext() == "host: str"
    assert params[1].astext() == "port: int = 5432"


def test_rebuild_signature_layout_strips_annotations_when_disabled() -> None:
    desc = _make_desc(ids=("demo.LayoutDemo.__init__",))
    sig = desc.children[0]
    assert isinstance(sig, addnodes.desc_signature)
    sig += addnodes.desc_name("", "__init__")
    plist = addnodes.desc_parameterlist()
    plist += _make_parameter("host", annotation="str")
    plist += _make_parameter("port", annotation="int", default="5432")
    sig += plist

    _rebuild_signature_layout(
        desc,
        sig,
        threshold=1,
        include_permalink=False,
        show_annotations=False,
    )

    layout = sig.children[0]
    assert isinstance(layout, api_component)
    left = layout.children[0]
    assert isinstance(left, api_component)
    signature = left.children[0]
    assert isinstance(signature, api_component)
    expanded = _find_component(signature, "api-signature-expanded")
    expanded_plist = expanded.children[0]
    assert isinstance(expanded_plist, addnodes.desc_parameterlist)
    assert expanded_plist.get("multi_line_parameter_list") is True
    assert expanded_plist.get("multi_line_trailing_comma") is False
    params = list(expanded_plist.findall(addnodes.desc_parameter))

    assert params[0].astext() == "host"
    assert params[1].astext() == "port=5432"


def test_rebuild_signature_layout_skips_multiline_signatures() -> None:
    desc = _make_desc(ids=("demo.func",))
    sig = desc.children[0]
    assert isinstance(sig, addnodes.desc_signature)
    sig["is_multiline"] = True
    sig += addnodes.desc_signature_line()
    original = list(sig.children)

    _rebuild_signature_layout(
        desc,
        sig,
        threshold=10,
        include_permalink=True,
        show_annotations=True,
    )

    assert list(sig.children) == original


def test_on_doctree_resolved_marks_managed_headers_with_initial_state() -> None:
    desc = _make_desc(ids=("demo.func",))
    sig = desc.children[0]
    assert isinstance(sig, addnodes.desc_signature)
    sig += addnodes.desc_name("", "func")
    sig += _make_parameter_list(2)

    app = t.cast(
        t.Any,
        types.SimpleNamespace(
            config=types.SimpleNamespace(
                gal_enabled=True,
                gal_collapsed_threshold=10,
                gal_fold_parameters=True,
                gal_signature_show_annotations=True,
                html_permalinks=True,
            ),
            builder=types.SimpleNamespace(format="html", add_permalinks=True),
        ),
    )
    doctree = t.cast(nodes.document, nodes.section("", desc))

    on_doctree_resolved(app, doctree, "index")

    assert sig.get("html_attrs") == {"data-signature-expanded": "false"}
