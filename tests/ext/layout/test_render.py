"""Tests for shared layout rendering helpers."""

from __future__ import annotations

from docutils import nodes
from docutils.statemachine import StringList
from sphinx import addnodes
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
