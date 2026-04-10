"""Sphinx directives for FastMCP tool documentation."""

from __future__ import annotations

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx_autodoc_layout import (
    ApiFactRow,
    api_permalink,
    build_api_card_entry,
    build_api_facts_section,
    build_api_section,
    build_api_summary_section,
    build_api_table_section,
)
from sphinx_typehints_gp import build_annotation_paragraph, classify_annotation_display

from sphinx_autodoc_fastmcp._badges import build_tool_badge_group
from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_autodoc_fastmcp._models import ParamInfo, ToolInfo
from sphinx_autodoc_fastmcp._parsing import (
    first_paragraph,
    make_literal,
    make_para,
    make_table,
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
        """Build section card with shared API layout regions."""
        document = self.state.document
        section_id = tool.name.replace("_", "-")

        section = nodes.section()
        section["ids"].append(section_id)
        section["classes"].extend((_CSS.TOOL_SECTION, "gal-card-shell"))
        document.note_explicit_target(section)

        title_node = nodes.title("", "")
        title_node["classes"].append(f"{_CSS.PREFIX}-tool-title")
        title_node["classes"].append(_CSS.SECTION_TITLE_HIDDEN)
        title_node += nodes.literal("", tool.name)
        section += title_node

        link = api_permalink(
            href=f"#{section_id}",
            title="Link to this tool",
        )
        link["classes"] = ["headerlink", "api-link"]
        first_para = first_paragraph(tool.docstring)
        content_nodes: list[nodes.Node] = [
            build_api_section(
                "api-description",
                parse_rst_inline(first_para, self.state, self.lineno),
                classes=(_CSS.BODY_SECTION,),
            )
        ]

        if tool.return_annotation:
            content_nodes.append(
                build_api_facts_section(
                    [
                        ApiFactRow(
                            "Returns",
                            build_annotation_paragraph(
                                tool.return_annotation,
                                self.env,
                            ),
                        )
                    ],
                    classes=(_CSS.BODY_SECTION,),
                )
            )

        entry = build_api_card_entry(
            profile_class="api-profile--fastmcp-tool",
            signature_children=(nodes.literal("", tool.name),),
            content_children=tuple(content_nodes),
            badge_group=build_tool_badge_group(tool.safety),
            permalink=link,
            entry_classes=(_CSS.TOOL_ENTRY,),
            signature_classes=(_CSS.TOOL_SIGNATURE,),
        )
        section += entry

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
                type_display = classify_annotation_display(p.type_str)

                type_cell: str | nodes.Node = "—"
                if type_display.text:
                    if type_display.is_literal_enum:
                        type_cell = make_para(make_literal("enum"))
                    else:
                        type_cell = build_annotation_paragraph(
                            type_display.text,
                            self.env,
                        )

                if type_display.literal_members:
                    desc_node += nodes.Text(" One of: ")
                    for i, val in enumerate(type_display.literal_members):
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
                build_api_table_section(
                    "api-parameters",
                    make_table(headers, rows, col_widths=[15, 15, 8, 10, 52]),
                ),
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
            section += build_api_summary_section(
                make_table(headers, rows, col_widths=[30, 70]),
            )

            result_nodes.append(section)

        return result_nodes
