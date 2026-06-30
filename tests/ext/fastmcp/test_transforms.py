"""Focused tests for FastMCP doctree transforms."""

from __future__ import annotations

import logging
import types
import typing as t

import pytest
from docutils import nodes
from sphinx.application import Sphinx

from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_autodoc_fastmcp._roles import _tool_ref_placeholder
from sphinx_autodoc_fastmcp._transforms import (
    collect_tool_section_content,
    resolve_tool_refs,
)
from sphinx_ux_autodoc_layout import build_api_component


def test_collect_tool_section_content_appends_siblings_to_api_content() -> None:
    doctree = nodes.section()
    tool_section = nodes.section(ids=["list-sessions"])
    tool_section["classes"] = [_CSS.TOOL_SECTION]
    entry = build_api_component("gp-sphinx-api-entry", classes=(_CSS.TOOL_ENTRY,))
    content = build_api_component("gp-sphinx-api-content")
    entry += content
    tool_section += entry
    trailing = nodes.paragraph("", "Parameters")
    doctree += tool_section
    doctree += trailing

    collect_tool_section_content(t.cast(t.Any, None), t.cast(nodes.document, doctree))

    assert trailing.parent is content
    assert list(content.children) == [trailing]


def _resolve_single_tool_ref(
    *,
    reftarget: str,
    labels: dict[str, tuple[str, str, str]],
    tools: dict[str, object],
    fromdocname: str = "index",
) -> nodes.Element:
    """Run ``resolve_tool_refs`` over one placeholder against a stubbed app.

    Returns the container so the caller can inspect the replacement node. The
    Sphinx ``app``/``builder``/``env`` are stubbed because the warning branch
    fires only for a tool whose every directive carries ``:no-index:`` — a
    state that is awkward to stage inside a full build but trivial to express
    as a label table missing the canonical id.
    """
    container = nodes.section()
    container += _tool_ref_placeholder("", reftarget=reftarget, show_badge=False)

    std = types.SimpleNamespace(labels=labels, anonlabels={})
    builder = types.SimpleNamespace(
        get_relative_uri=lambda _frm, todoc: f"{todoc}.html",
    )
    env = types.SimpleNamespace(
        domains=types.SimpleNamespace(standard_domain=std),
        fastmcp_tools=tools,
    )
    app = types.SimpleNamespace(env=env, builder=builder)

    resolve_tool_refs(
        t.cast(Sphinx, app),
        t.cast(nodes.document, container),
        fromdocname,
    )
    return container


def test_resolve_tool_refs_warns_when_known_tool_has_no_canonical_home(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A known tool resolving to a foreign label (reserved ``search``) warns."""
    with caplog.at_level(logging.WARNING, logger="sphinx_autodoc_fastmcp._transforms"):
        container = _resolve_single_tool_ref(
            reftarget="search",
            labels={"search": ("search", "", "Search Page")},
            tools={"search": object()},
        )

    records = [
        r for r in caplog.records if r.name == "sphinx_autodoc_fastmcp._transforms"
    ]
    assert len(records) == 1
    message = records[0].getMessage()
    assert "'search'" in message
    assert "canonical section 'fastmcp-tool-search'" in message
    # The link still renders (to the foreign label) rather than vanishing.
    assert isinstance(container[0], nodes.reference)


def test_resolve_tool_refs_silent_when_canonical_label_present(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No warning when the canonical ``fastmcp-tool-<slug>`` label exists."""
    with caplog.at_level(logging.WARNING, logger="sphinx_autodoc_fastmcp._transforms"):
        container = _resolve_single_tool_ref(
            reftarget="search",
            labels={
                "search": ("search", "", "Search Page"),
                "fastmcp-tool-search": (
                    "mcp/tools",
                    "fastmcp-tool-search",
                    "search",
                ),
            },
            tools={"search": object()},
        )

    warnings = [
        r for r in caplog.records if r.name == "sphinx_autodoc_fastmcp._transforms"
    ]
    assert warnings == []
    reference = container[0]
    assert isinstance(reference, nodes.reference)
    assert reference["refuri"] == "mcp/tools.html#fastmcp-tool-search"
