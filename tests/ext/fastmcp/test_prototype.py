"""Tests for the non-shipping FastMCP ``desc`` prototype."""

from __future__ import annotations

import types
import typing as t

from docutils import nodes
from sphinx import addnodes

from sphinx_autodoc_fastmcp._models import ParamInfo, ToolInfo
from sphinx_autodoc_fastmcp._prototype import build_tool_desc_prototype
from sphinx_autodoc_layout._nodes import api_component, api_sig_fold
from sphinx_autodoc_layout._transforms import on_doctree_resolved


def _make_tool_info() -> ToolInfo:
    return ToolInfo(
        name="list_sessions",
        title="List Sessions",
        module_name="demo_tools",
        area="api",
        safety="readonly",
        annotations={},
        func=lambda server: "[]",
        docstring="List sessions for one server.\n\nReturns the available sessions.",
        params=[
            ParamInfo("server", "str", True, "", "Server name."),
            ParamInfo("limit", "int", False, "20", "Maximum number to return."),
            ParamInfo("cursor", "str | None", False, "None", "Pagination cursor."),
            ParamInfo("project", "str | None", False, "None", "Project filter."),
            ParamInfo("status", "'open' | 'closed'", False, "'open'", "Status filter."),
            ParamInfo("owner", "str | None", False, "None", "Owner filter."),
            ParamInfo("region", "str | None", False, "None", "Region filter."),
            ParamInfo("updated_after", "str | None", False, "None", "Updated filter."),
            ParamInfo("updated_before", "str | None", False, "None", "Updated filter."),
            ParamInfo("include_archived", "bool", False, "False", "Archive filter."),
            ParamInfo("expand", "str | None", False, "None", "Expansion options."),
            ParamInfo("request_id", "str | None", False, "None", "Request id."),
        ],
        return_annotation="str",
    )


def _find_component(node: nodes.Element, name: str) -> api_component:
    for child in node.children:
        if isinstance(child, api_component) and child.get("name") == name:
            return child
    raise AssertionError(f"component not found: {name}")


def _rendered_desc() -> addnodes.desc:
    desc = build_tool_desc_prototype(_make_tool_info())
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
    return desc


def test_build_tool_desc_prototype_uses_mcp_tool_shape() -> None:
    desc = build_tool_desc_prototype(_make_tool_info())

    assert desc.get("domain") == "mcp"
    assert desc.get("objtype") == "tool"
    signature = desc.children[0]
    assert isinstance(signature, addnodes.desc_signature)
    assert signature.get("ids") == ["list-sessions"]
    assert any(
        isinstance(child, nodes.Element) and child.get("slot") == "badges"
        for child in signature.children
    )
    assert any(
        isinstance(child, addnodes.desc_parameterlist) for child in signature.children
    )

    content = desc.children[1]
    assert isinstance(content, addnodes.desc_content)
    assert any(isinstance(child, nodes.field_list) for child in content.children)


def test_build_tool_desc_prototype_reflows_under_shared_layout() -> None:
    desc = _rendered_desc()

    assert "api-profile--mcp-tool" in desc.get("classes", [])
    signature = desc.children[0]
    assert isinstance(signature, addnodes.desc_signature)
    layout = _find_component(signature, "api-layout")
    left = _find_component(layout, "api-layout-left")
    right = _find_component(layout, "api-layout-right")
    body = desc.children[1]
    assert isinstance(body, addnodes.desc_content)

    assert _find_component(left, "api-signature")
    assert "sab-toolbar" in right.get("classes", [])
    assert any(
        isinstance(node, api_sig_fold) for node in signature.findall(api_sig_fold)
    )
    assert any(
        isinstance(child, api_component) and child.get("name") == "api-parameters"
        for child in body.children
    )
