"""Doctree hooks for labels, section badges, and tool reference resolution."""

from __future__ import annotations

import logging
import re

from docutils import nodes
from sphinx.application import Sphinx

from sphinx_autodoc_fastmcp._badges import build_safety_badge
from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_autodoc_fastmcp._models import ToolInfo
from sphinx_autodoc_fastmcp._roles import _tool_ref_placeholder
from sphinx_ux_autodoc_layout import API, api_component
from sphinx_ux_badges import SAB

logger = logging.getLogger(__name__)


def _tool_content_container(section: nodes.section) -> nodes.Element:
    """Return the shared content wrapper for a FastMCP tool section."""
    for child in section.children:
        if not isinstance(child, api_component) or child.get("name") != API.ENTRY:
            continue
        for grandchild in child.children:
            if isinstance(grandchild, api_component) and grandchild.get("name") == (
                API.CONTENT
            ):
                return grandchild
    return section


def collect_tool_section_content(app: Sphinx, doctree: nodes.document) -> None:
    """Move siblings following each tool section into the section.

    Directive-returned ``nodes.section`` is a closed node — MyST does not
    "enter" it.  This transform runs after parsing and re-parents prose,
    code blocks, and ``{fastmcp-tool-input}`` tables that sit between one
    tool section and the next boundary (``---`` transition or another tool
    section).
    """
    for section in list(doctree.findall(nodes.section)):
        if _CSS.TOOL_SECTION not in section.get("classes", []):
            continue
        parent = section.parent
        if parent is None:
            continue
        content = _tool_content_container(section)
        idx = parent.index(section)
        while idx + 1 < len(parent.children):
            sibling = parent.children[idx + 1]
            if isinstance(sibling, nodes.transition):
                parent.remove(sibling)
                break
            if isinstance(sibling, nodes.section):
                break
            parent.remove(sibling)
            content.append(sibling)


def register_tool_labels(app: Sphinx, doctree: nodes.document) -> None:
    """Mirror autosectionlabel for tool sections (``{ref}`tool-id```)."""
    domain = app.env.domains.standard_domain
    docname = app.env.docname
    for section in doctree.findall(nodes.section):
        if not section["ids"]:
            continue
        section_id = section["ids"][0]
        if section.children and isinstance(section[0], nodes.title):
            title_node = section[0]
            tool_name = ""
            for child in title_node.children:
                if isinstance(child, nodes.literal):
                    tool_name = child.astext()
                    break
            if not tool_name:
                continue
            domain.anonlabels[section_id] = (docname, section_id)
            domain.labels[section_id] = (docname, section_id, tool_name)


def add_section_badges(
    app: Sphinx,
    doctree: nodes.document,
    fromdocname: str,
) -> None:
    """Add safety badges to tier headings on configured pages."""
    pages: set[str] = set(app.config.fastmcp_section_badge_pages)
    badge_map: dict[str, str] = dict(app.config.fastmcp_section_badge_map)
    if fromdocname not in pages:
        return
    for section in doctree.findall(nodes.section):
        if not section.children or not isinstance(section[0], nodes.title):
            continue
        title_text = section[0].astext().strip()

        safety = badge_map.get(title_text)
        if safety is not None:
            section[0] += nodes.Text(" ")
            section[0] += build_safety_badge(safety)
            continue

        m = re.match(r"^(\w+)\s*\((\w+)\)$", title_text)
        if m:
            heading, tier = m.group(1), m.group(2)
            if heading in badge_map and tier == badge_map[heading]:
                title_node = section[0]
                title_node.clear()
                title_node += nodes.Text(heading + " ")
                title_node += build_safety_badge(tier)


def resolve_tool_refs(
    app: Sphinx,
    doctree: nodes.document,
    fromdocname: str,
) -> None:
    """Resolve ``:tool:`` / ``:toolref:`` / ``:toolicon*:`` placeholders."""
    domain = app.env.domains.standard_domain
    builder = app.builder
    tool_data: dict[str, ToolInfo] = getattr(app.env, "fastmcp_tools", {})

    for node in list(doctree.findall(_tool_ref_placeholder)):
        target = node.get("reftarget", "")
        show_badge = node.get("show_badge", True)
        icon_pos = node.get("icon_pos", "")
        label_info = domain.labels.get(target)
        if label_info is None:
            node.replace_self(nodes.literal("", target.replace("-", "_")))
            continue

        todocname, labelid, _title = label_info
        tool_name = target.replace("-", "_")

        newnode = nodes.reference("", "", internal=True)
        try:
            newnode["refuri"] = builder.get_relative_uri(fromdocname, todocname)
            if labelid:
                newnode["refuri"] += "#" + labelid
        except Exception:
            logger.warning(
                "sphinx_autodoc_fastmcp: failed to resolve URI for %s -> %s",
                fromdocname,
                todocname,
            )
            newnode["refuri"] = "#" + labelid
        newnode["classes"].append("reference")
        newnode["classes"].append("internal")

        if icon_pos:
            tool_info = tool_data.get(tool_name)
            badge = None
            if tool_info:
                style = "inline-icon" if icon_pos.startswith("inline") else "icon-only"
                badge = build_safety_badge(tool_info.safety, icon_only=True)
                if style == "inline-icon":
                    badge["classes"].append(SAB.INLINE_ICON)

            if icon_pos == "left":
                if badge:
                    newnode += badge
                newnode += nodes.literal("", tool_name)
            elif icon_pos == "right":
                newnode += nodes.literal("", tool_name)
                if badge:
                    newnode += badge
            elif icon_pos == "inline-left":
                code_node = nodes.literal("", "")
                if badge:
                    code_node += badge
                code_node += nodes.Text(tool_name)
                newnode += code_node
            elif icon_pos == "inline-right":
                code_node = nodes.literal("", "")
                code_node += nodes.Text(tool_name)
                if badge:
                    code_node += badge
                newnode += code_node
        else:
            newnode += nodes.literal("", tool_name)
            if show_badge:
                tool_info = tool_data.get(tool_name)
                if tool_info:
                    newnode += nodes.Text(" ")
                    newnode += build_safety_badge(tool_info.safety)

        node.replace_self(newnode)


def badge_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: object,
    options: dict[str, object] | None = None,
    content: list[str] | None = None,
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    """Role ``:badge:`readonly``` → safety badge."""
    return [build_safety_badge(text.strip())], []
