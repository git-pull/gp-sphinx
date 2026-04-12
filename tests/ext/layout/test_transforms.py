"""Tests for sphinx_autodoc_layout._transforms."""

from __future__ import annotations

import types
import typing as t

from docutils import nodes
from sphinx import addnodes

from sphinx_autodoc_layout._nodes import (
    api_component,
    api_fold,
    api_inline_component,
    api_permalink,
    api_sig_fold,
    api_slot,
    build_api_slot,
)
from sphinx_autodoc_layout._sections import ApiFactRow, build_api_facts_section
from sphinx_autodoc_layout._transforms import (
    DescLayoutProfile,
    _classify_child,
    _count_field_entries,
    _desc_layout_profile,
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


def _make_badge_slot() -> api_slot:
    badge_group = nodes.inline(classes=["sab-badge-group"])
    badge_group += nodes.inline("", "method", classes=["sab-badge"])
    return build_api_slot("badges", badge_group)


def _make_source_slot() -> api_slot:
    source_span = nodes.inline(classes=["viewcode-link"])
    source_span += nodes.Text("[source]")
    source_ref = nodes.reference("", "", source_span, internal=False)
    return build_api_slot("source-link", source_ref)


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


def test_desc_layout_profile_matches_confval_entries() -> None:
    profile = _desc_layout_profile(_make_desc(domain="std", objtype="confval"))
    assert profile == DescLayoutProfile(
        domain="std",
        objtype="confval",
        slug="confval",
        allow_signature_fold=False,
    )
    assert profile.class_name == "api-profile--confval"


def test_desc_layout_profile_matches_rst_directive_option_entries() -> None:
    profile = _desc_layout_profile(
        _make_desc(domain="rst", objtype="directive:option"),
    )
    assert profile == DescLayoutProfile(
        domain="rst",
        objtype="directive:option",
        slug="rst-directive-option",
        allow_signature_fold=False,
    )


def test_desc_layout_profile_matches_mcp_tool_entries() -> None:
    profile = _desc_layout_profile(
        _make_desc(domain="mcp", objtype="tool"),
    )
    assert profile == DescLayoutProfile(
        domain="mcp",
        objtype="tool",
        slug="mcp-tool",
        allow_signature_fold=True,
    )


def test_desc_layout_profile_covers_all_managed_non_python_entries() -> None:
    expected = {
        ("py", "fixture"): "api-profile--py-fixture",
        ("std", "confval"): "api-profile--confval",
        ("rst", "directive"): "api-profile--rst-directive",
        ("rst", "role"): "api-profile--rst-role",
        ("rst", "directive:option"): "api-profile--rst-directive-option",
        ("mcp", "tool"): "api-profile--mcp-tool",
    }

    for (domain, objtype), class_name in expected.items():
        profile = _desc_layout_profile(_make_desc(domain=domain, objtype=objtype))
        assert profile is not None
        assert profile.class_name == class_name


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
    assert "api-region" in section.get("classes", [])
    assert len(section.children) == 2


def test_wrap_preserves_prebuilt_fact_sections() -> None:
    desc = _make_desc(
        nodes.paragraph("", "intro"),
    )
    content = t.cast(addnodes.desc_content, desc.children[-1])
    content += build_api_facts_section(
        [
            ApiFactRow(
                "Type",
                nodes.paragraph("", "", nodes.literal("", "bool")),
            )
        ]
    )

    _wrap_content_runs(desc)

    assert _child_component_names(content) == ["api-description", "api-facts"]


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
    section["classes"] = ["api-parameters", "api-region", "api-region--fields"]
    section += _make_field_list(12)
    content += section

    _fold_large_field_regions(content, threshold=10)

    fold = section.children[0]
    assert isinstance(fold, api_fold)
    assert fold.get("summary") == "Parameters (12)"
    assert isinstance(fold.children[0], nodes.field_list)


def test_fold_wraps_sphinx_collapsed_field_list() -> None:
    content = addnodes.desc_content()
    section = api_component(name="api-parameters", tag="div")
    section["classes"] = ["api-parameters", "api-region", "api-region--fields"]
    section += _make_sphinx_field_list(13)
    content += section

    _fold_large_field_regions(content, threshold=10)

    fold = section.children[0]
    assert isinstance(fold, api_fold)
    assert fold.get("summary") == "Parameters (13)"


def test_fold_skips_small_field_list() -> None:
    content = addnodes.desc_content()
    section = api_component(name="api-parameters", tag="div")
    section["classes"] = ["api-parameters", "api-region", "api-region--fields"]
    fl = _make_field_list(5)
    section += fl
    content += section

    _fold_large_field_regions(content, threshold=10)

    assert isinstance(section.children[0], nodes.field_list)
    assert not isinstance(section.children[0], api_fold)


def test_fold_skips_non_parameter_sections() -> None:
    content = addnodes.desc_content()
    section = api_component(name="api-description", tag="div")
    section["classes"] = ["api-description", "api-region", "api-region--narrative"]
    section += nodes.paragraph("", "text")
    content += section

    _fold_large_field_regions(content, threshold=1)

    assert isinstance(section.children[0], nodes.paragraph)


def test_rebuild_signature_layout_splits_slots_and_permalink() -> None:
    desc = _make_desc(ids=("demo.func",))
    sig = desc.children[0]
    assert isinstance(sig, addnodes.desc_signature)
    sig += addnodes.desc_name("", "func")
    sig += _make_parameter_list(2)
    sig += _make_badge_slot()
    sig += _make_source_slot()

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
    sig += _make_badge_slot()
    sig += _make_source_slot()

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
    assert any(isinstance(child, api_sig_fold) for child in signature.children)
    expanded = _find_component(signature, "api-signature-expanded")
    html_attrs = t.cast(dict[str, str], expanded.get("html_attrs", {}))
    assert html_attrs.get("id") == ("demo.LayoutDemo.__init__--signature-expanded")
    plist = expanded.children[0]
    assert isinstance(plist, addnodes.desc_parameterlist)
    assert plist.get("multi_line_parameter_list") is True
    assert plist.get("multi_line_trailing_comma") is False
    collapse = expanded.children[1]
    assert isinstance(collapse, api_inline_component)
    assert collapse.get("name") == "api-sig-collapse"
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
                api_layout_enabled=True,
                api_collapsed_threshold=10,
                api_fold_parameters=True,
                api_signature_show_annotations=True,
                html_permalinks=True,
            ),
            builder=types.SimpleNamespace(format="html", add_permalinks=True),
        ),
    )
    doctree = t.cast(nodes.document, nodes.section("", desc))

    on_doctree_resolved(app, doctree, "index")

    assert sig.get("html_attrs") == {"data-signature-expanded": "false"}


def test_on_doctree_resolved_manages_slot_backed_headers_without_gal_enabled() -> None:
    desc = _make_desc(ids=("demo.func",))
    sig = desc.children[0]
    assert isinstance(sig, addnodes.desc_signature)
    sig += addnodes.desc_name("", "func")
    sig += _make_badge_slot()

    app = t.cast(
        t.Any,
        types.SimpleNamespace(
            config=types.SimpleNamespace(
                api_layout_enabled=False,
                api_collapsed_threshold=10,
                api_fold_parameters=True,
                api_signature_show_annotations=True,
                html_permalinks=True,
            ),
            builder=types.SimpleNamespace(format="html", add_permalinks=True),
        ),
    )
    doctree = t.cast(nodes.document, nodes.section("", desc))

    on_doctree_resolved(app, doctree, "index")

    assert "api-container" in desc.get("classes", [])
    layout = sig.children[0]
    assert isinstance(layout, api_component)
    right = layout.children[1]
    assert isinstance(right, api_component)
    assert _child_component_names(right) == ["api-badge-container"]


def test_on_doctree_resolved_manages_confval_entries_with_profile_classes() -> None:
    desc = _make_desc(domain="std", objtype="confval", ids=("confval.demo_option",))
    sig = desc.children[0]
    assert isinstance(sig, addnodes.desc_signature)
    sig += addnodes.desc_name("", "demo_option")
    sig += _make_badge_slot()

    app = t.cast(
        t.Any,
        types.SimpleNamespace(
            config=types.SimpleNamespace(
                api_layout_enabled=False,
                api_collapsed_threshold=10,
                api_fold_parameters=True,
                api_signature_show_annotations=True,
                html_permalinks=True,
            ),
            builder=types.SimpleNamespace(format="html", add_permalinks=True),
        ),
    )
    doctree = t.cast(nodes.document, nodes.section("", desc))

    on_doctree_resolved(app, doctree, "index")

    assert "api-container" in desc.get("classes", [])
    assert "api-profile--confval" in desc.get("classes", [])
    layout = sig.children[0]
    assert isinstance(layout, api_component)
    right = layout.children[1]
    assert isinstance(right, api_component)
    assert _child_component_names(right) == ["api-badge-container"]
