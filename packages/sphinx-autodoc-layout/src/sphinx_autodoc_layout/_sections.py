"""Shared body-section builders for componentized autodoc entries.

Examples
--------
>>> from docutils import nodes
>>> from sphinx_autodoc_layout._sections import ApiFactRow, build_api_facts_section
>>> section = build_api_facts_section(
...     [ApiFactRow("Type", nodes.paragraph("", "", nodes.literal("", "bool")))]
... )
>>> section.get("name")
'api-facts'
"""

from __future__ import annotations

import typing as t
from dataclasses import dataclass

from docutils import nodes

from sphinx_autodoc_layout._nodes import api_component, build_api_component

_SECTION_KIND_CLASS: dict[str, str] = {
    "api-description": "narrative",
    "api-facts": "facts",
    "api-parameters": "fields",
    "api-options": "options",
    "api-footer": "members",
}


@dataclass(frozen=True, slots=True)
class ApiFactRow:
    """Typed fact row rendered inside a shared ``api-facts`` section.

    Parameters
    ----------
    label : str
        Field label displayed in the facts grid.
    body : nodes.Node
        Node rendered as the field body.
    """

    label: str
    body: nodes.Node


def build_api_section(
    name: str,
    *children: nodes.Node,
    classes: tuple[str, ...] = (),
) -> api_component:
    """Return a shared API body section with stable region classes."""
    kind = _SECTION_KIND_CLASS.get(name)
    region_classes = ("gal-region", f"gal-region--{kind}") if kind is not None else ()
    section = build_api_component(name, classes=(*region_classes, *classes))
    for child in children:
        section += child
    return section


def build_api_facts_section(
    rows: t.Sequence[ApiFactRow],
    *,
    classes: tuple[str, ...] = (),
) -> api_component:
    """Render a shared ``api-facts`` section from typed fact rows."""
    field_list = nodes.field_list(classes=["api-facts-list"])
    for row in rows:
        field_body = nodes.field_body()
        field_body += row.body
        field_list += nodes.field(
            "",
            nodes.field_name("", row.label),
            field_body,
        )
    return build_api_section("api-facts", field_list, classes=classes)


def build_api_table_section(
    name: str,
    *children: nodes.Node,
    classes: tuple[str, ...] = (),
) -> api_component:
    """Wrap one or more table-like body nodes in a shared API section."""
    return build_api_section(name, *children, classes=classes)
