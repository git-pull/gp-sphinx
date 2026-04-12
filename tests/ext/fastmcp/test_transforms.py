"""Focused tests for FastMCP doctree transforms."""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_autodoc_fastmcp._transforms import collect_tool_section_content
from sphinx_ux_autodoc_layout import build_api_component


def test_collect_tool_section_content_appends_siblings_to_api_content() -> None:
    doctree = nodes.section()
    tool_section = nodes.section(ids=["list-sessions"])
    tool_section["classes"] = [_CSS.TOOL_SECTION]
    entry = build_api_component("api-entry", classes=(_CSS.TOOL_ENTRY,))
    content = build_api_component("api-content")
    entry += content
    tool_section += entry
    trailing = nodes.paragraph("", "Parameters")
    doctree += tool_section
    doctree += trailing

    collect_tool_section_content(t.cast(t.Any, None), t.cast(nodes.document, doctree))

    assert trailing.parent is content
    assert list(content.children) == [trailing]
