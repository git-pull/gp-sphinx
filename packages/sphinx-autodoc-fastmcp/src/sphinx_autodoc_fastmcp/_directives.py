"""Sphinx directives for FastMCP tool documentation."""

from __future__ import annotations

from docutils import nodes
from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_fastmcp._badges import build_toolbar
from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_autodoc_fastmcp._models import ParamInfo, ToolInfo
from sphinx_autodoc_fastmcp._parsing import (
    extract_enum_values as extract_enum_values_from_type,
    first_paragraph,
    make_para,
    make_table,
    make_type_cell_smart,
    make_type_xref,
    parse_rst_inline,
)


class FastMCPToolDirective(SphinxDirective):
    """Autodocument one MCP tool: section (ToC/labels) + card body."""

    required_arguments = 1
    optional_arguments = 0
    has_content = True
    final_argument_whitespace = False

    def run(self) -> list[nodes.Node]:
        """Build section with title row + docstring/returns for one tool."""
        arg = self.arguments[0]
        func_name = arg.split(".")[-1] if "." in arg else arg

        tools: dict[str, ToolInfo] = getattr(self.env, "fastmcp_tools", {})
        tool = tools.get(func_name)

        if tool is None:
            return [
                self.state.document.reporter.warning(
                    f"fastmcp-tool: tool '{func_name}' not found. "
                    f"Available: {', '.join(sorted(tools.keys()))}",
                    line=self.lineno,
                ),
            ]

        return self._build_tool_section(tool)

    def _build_tool_section(self, tool: ToolInfo) -> list[nodes.Node]:
        """Build section card: title (literal + badges) + summary + returns."""
        document = self.state.document
        section_id = tool.name.replace("_", "-")

        section = nodes.section()
        section["ids"].append(section_id)
        section["classes"].append(_CSS.TOOL_SECTION)
        document.note_explicit_target(section)

        title_node = nodes.title("", "")
        title_node["classes"].append(f"{_CSS.PREFIX}-tool-title")
        title_node += nodes.literal("", tool.name)
        title_node += nodes.Text(" ")
        title_node += build_toolbar(tool.safety)
        section += title_node

        first_para = first_paragraph(tool.docstring)
        section += parse_rst_inline(first_para, self.state, self.lineno)

        if tool.return_annotation:
            returns_para = nodes.paragraph("")
            returns_para += nodes.strong("", "Returns: ")
            type_para = make_type_xref(
                tool.return_annotation,
                model_module=str(self.config.fastmcp_model_module),
                model_classes=frozenset(self.config.fastmcp_model_classes),
            )
            for child in type_para.children:
                returns_para += child.deepcopy()
            section += returns_para

        return [section]


class FastMCPToolInputDirective(SphinxDirective):
    """Emit the parameter table for a tool."""

    required_arguments = 1
    optional_arguments = 0
    has_content = False

    def run(self) -> list[nodes.Node]:
        """Build parameter table nodes."""
        arg = self.arguments[0]
        func_name = arg.split(".")[-1] if "." in arg else arg

        tools: dict[str, ToolInfo] = getattr(self.env, "fastmcp_tools", {})
        tool = tools.get(func_name)

        if tool is None:
            return [
                self.state.document.reporter.warning(
                    f"fastmcp-tool-input: tool '{func_name}' not found.",
                    line=self.lineno,
                ),
            ]

        result: list[nodes.Node] = []

        if tool.params:
            result.append(make_para(nodes.strong("", "Parameters")))
            headers = ["Parameter", "Type", "Required", "Default", "Description"]
            rows: list[list[str | nodes.Node]] = []
            for p in tool.params:
                desc_node = self._build_description(p)

                type_cell, is_enum = make_type_cell_smart(p.type_str)

                if is_enum and p.type_str:
                    enum_values = extract_enum_values_from_type(p.type_str)
                    if enum_values:
                        desc_node += nodes.Text(" One of: ")
                        for i, val in enumerate(enum_values):
                            if i > 0:
                                desc_node += nodes.Text(", ")
                            desc_node += nodes.literal("", val)
                        desc_node += nodes.Text(".")

                default_cell: str | nodes.Node = "—"
                if p.default and p.default != "None":
                    default_cell = make_para(nodes.literal("", p.default))

                rows.append(
                    [
                        make_para(nodes.literal("", p.name)),
                        type_cell,
                        "yes" if p.required else "no",
                        default_cell,
                        desc_node,
                    ],
                )
            result.append(
                make_table(headers, rows, col_widths=[15, 15, 8, 10, 52]),
            )

        return result

    def _build_description(self, p: ParamInfo) -> nodes.paragraph:
        """Build description paragraph with optional RST inline markup."""
        if p.description:
            return parse_rst_inline(
                p.description,
                self.state,
                self.lineno,
            )
        return nodes.paragraph("", "—")


class FastMCPToolSummaryDirective(SphinxDirective):
    """Summary tables of tools grouped by safety tier."""

    required_arguments = 0
    optional_arguments = 0
    has_content = False

    def run(self) -> list[nodes.Node]:
        """Build tier sections with tables."""
        tools: dict[str, ToolInfo] = getattr(self.env, "fastmcp_tools", {})

        if not tools:
            return [
                self.state.document.reporter.warning(
                    "fastmcp-toolsummary: no tools found.",
                    line=self.lineno,
                ),
            ]

        groups: dict[str, list[ToolInfo]] = {
            "readonly": [],
            "mutating": [],
            "destructive": [],
        }
        for tool in tools.values():
            groups.setdefault(tool.safety, []).append(tool)

        result_nodes: list[nodes.Node] = []

        tier_order = [
            ("readonly", "Inspect", "Read state without changing anything."),
            ("mutating", "Act", "Create or modify objects."),
            ("destructive", "Destroy", "Remove objects; not reversible."),
        ]

        for safety, label, desc in tier_order:
            tier_tools = groups.get(safety, [])
            if not tier_tools:
                continue

            section = nodes.section()
            section["ids"].append(label.lower())
            self.state.document.note_explicit_target(section)
            section += nodes.title("", label)
            section += nodes.paragraph("", desc)

            headers = ["Tool", "Description"]
            rows: list[list[str | nodes.Node]] = []
            for tool in sorted(tier_tools, key=lambda x: x.name):
                first_line = first_paragraph(tool.docstring)
                ref = nodes.reference("", "", internal=True)
                ref["refuri"] = f"{tool.area}/#{tool.name.replace('_', '-')}"
                ref += nodes.literal("", tool.name)
                rows.append(
                    [
                        make_para(ref),
                        parse_rst_inline(first_line, self.state, self.lineno),
                    ],
                )
            section += make_table(headers, rows, col_widths=[30, 70])

            result_nodes.append(section)

        return result_nodes
