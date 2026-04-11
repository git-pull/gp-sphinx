"""Test-only FastMCP ``desc`` prototype builders.

These helpers are intentionally internal and non-shipping. They let the test
suite answer whether FastMCP tool metadata can fit a real ``addnodes.desc``
shape without changing the public directive output.

Examples
--------
>>> from sphinx_autodoc_fastmcp._models import ParamInfo, ToolInfo
>>> tool = ToolInfo(
...     name="list_sessions",
...     title="List Sessions",
...     module_name="demo_tools",
...     area="api",
...     safety="readonly",
...     annotations={},
...     func=lambda server: "[]",
...     docstring="List sessions for one server.",
...     params=[
...         ParamInfo(
...             name="server",
...             type_str="str",
...             required=True,
...             default="",
...             description="Server name.",
...         )
...     ],
...     return_annotation="str",
... )
>>> desc = build_tool_desc_prototype(tool)
>>> desc.get("domain"), desc.get("objtype")
('mcp', 'tool')
"""

from __future__ import annotations

from docutils import nodes
from sphinx import addnodes
from sphinx_autodoc_layout import inject_signature_slots
from sphinx_autodoc_typehints_gp import (
    build_annotation_display_paragraph,
    normalize_annotation_text,
)

from sphinx_autodoc_fastmcp._badges import build_tool_badge_group
from sphinx_autodoc_fastmcp._models import ParamInfo, ToolInfo
from sphinx_autodoc_fastmcp._parsing import (
    first_paragraph,
    make_para,
    make_table,
)


def _tool_desc_id(tool: ToolInfo) -> str:
    """Return the stable prototype id for *tool*."""
    return tool.name.replace("_", "-")


def _build_tool_parameter(param: ParamInfo) -> addnodes.desc_parameter:
    """Build one ``desc_parameter`` from FastMCP metadata."""
    node = addnodes.desc_parameter()
    node += addnodes.desc_sig_name("", param.name)
    if param.type_str:
        node += addnodes.desc_sig_punctuation("", ":")
        node += addnodes.desc_sig_space("", " ")
        node += nodes.emphasis("", normalize_annotation_text(param.type_str))
    if param.default:
        node += addnodes.desc_sig_space("", " ")
        node += addnodes.desc_sig_operator("", "=")
        node += addnodes.desc_sig_space("", " ")
        node += nodes.inline("", param.default, classes=["default_value"])
    return node


def _build_parameter_table(tool: ToolInfo) -> nodes.table:
    """Return the prototype parameter table for *tool*."""
    headers = ["Parameter", "Type", "Required", "Default", "Description"]
    rows: list[list[str | nodes.Node]] = []
    for param in tool.params:
        type_cell: str | nodes.Node = "—"
        if param.type_str:
            type_cell = build_annotation_display_paragraph(param.type_str, None)
        default_cell: str | nodes.Node = "—"
        if param.default:
            default_cell = make_para(nodes.literal("", param.default))
        description = (
            make_para(param.description)
            if param.description
            else nodes.paragraph("", "—")
        )
        rows.append(
            [
                make_para(nodes.literal("", param.name)),
                type_cell,
                "yes" if param.required else "no",
                default_cell,
                description,
            ]
        )
    return make_table(headers, rows, col_widths=[15, 15, 8, 10, 52])


def _build_parameter_fields(tool: ToolInfo) -> nodes.field_list:
    """Return a ``field_list`` wrapper around the parameter table."""
    field_list = nodes.field_list()
    if tool.params:
        field_list += nodes.field(
            "",
            nodes.field_name("", "Parameters"),
            nodes.field_body("", _build_parameter_table(tool)),
        )
    if tool.return_annotation:
        field_list += nodes.field(
            "",
            nodes.field_name("", "Returns"),
            nodes.field_body(
                "",
                build_annotation_display_paragraph(tool.return_annotation, None),
            ),
        )
    return field_list


def build_tool_desc_prototype(tool: ToolInfo) -> addnodes.desc:
    """Build a non-shipping ``mcp:tool`` description node for *tool*."""
    desc = addnodes.desc(domain="mcp", objtype="tool")
    signature = addnodes.desc_signature(ids=[_tool_desc_id(tool)])
    signature += addnodes.desc_name("", tool.name)
    if tool.params:
        parameter_list = addnodes.desc_parameterlist()
        for param in tool.params:
            parameter_list += _build_tool_parameter(param)
        signature += parameter_list
    inject_signature_slots(
        signature,
        marker_attr="smf_prototype_slots",
        badge_node=build_tool_badge_group(tool.safety),
        extract_source_link=False,
    )
    desc += signature

    content = addnodes.desc_content()
    summary = first_paragraph(tool.docstring)
    if summary:
        content += nodes.paragraph("", summary)
    parameter_fields = _build_parameter_fields(tool)
    if parameter_fields.children:
        content += parameter_fields
    desc += content
    return desc
