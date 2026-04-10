"""Tests for shared layout rendering helpers."""

from __future__ import annotations

import typing as t

from docutils import nodes
from docutils.statemachine import StringList
from sphinx import addnodes
from sphinx_autodoc_layout._cards import build_api_card_entry
from sphinx_autodoc_layout._nodes import api_permalink
from sphinx_autodoc_layout._render import iter_desc_nodes, parse_generated_markup


class _DummyState:
    def nested_parse(
        self,
        view_list: StringList,
        offset: int,
        node: nodes.Element,
    ) -> None:
        for line in view_list:
            node += nodes.paragraph("", line)


class _DummyDirective:
    state = _DummyState()
    content_offset = 0

    def get_source_info(self) -> tuple[str, int]:
        return ("demo.md", 1)


def test_parse_generated_markup_falls_back_to_nested_parse() -> None:
    rendered = parse_generated_markup(_DummyDirective(), "demo")  # type: ignore[arg-type]
    assert rendered[0].astext() == "demo"


def test_iter_desc_nodes_yields_nested_desc_entries() -> None:
    container = nodes.container()
    desc = addnodes.desc(domain="std", objtype="confval")
    container += desc

    assert list(iter_desc_nodes([container])) == [desc]


def test_build_api_card_entry_uses_shared_component_shell() -> None:
    """Non-desc card consumers can reuse the shared inner api shell."""
    entry = build_api_card_entry(
        profile_class="api-profile--demo",
        signature_children=(nodes.literal("", "demo_tool"),),
        content_children=(nodes.paragraph("", "Demo body."),),
        badge_group=nodes.inline("", "badge", classes=["sab-badge-group"]),
        permalink=api_permalink(href="#demo-tool", title="Permalink"),
        entry_classes=("demo-entry",),
        signature_classes=("demo-signature",),
    )

    assert entry.get("classes") == [
        "api-entry",
        "gal-card-entry",
        "api-profile--demo",
        "demo-entry",
    ]
    header = t.cast(nodes.Element, entry.children[0])
    content = t.cast(nodes.Element, entry.children[1])

    assert header.get("name") == "api-header"
    assert content.get("name") == "api-content"
    assert "demo_tool" in header.astext()
    assert "badge" in header.astext()
    assert "Demo body." in content.astext()
