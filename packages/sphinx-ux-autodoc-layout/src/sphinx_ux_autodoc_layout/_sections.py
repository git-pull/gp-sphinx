"""Shared body-section builders for componentized autodoc entries.

Examples
--------
>>> from docutils import nodes
>>> from sphinx_ux_autodoc_layout._sections import (
...     ApiFactRow,
...     build_api_facts_section,
...     build_api_summary_section,
... )
>>> section = build_api_facts_section(
...     [ApiFactRow("Type", nodes.paragraph("", "", nodes.literal("", "bool")))]
... )
>>> section.get("name")
'gp-sphinx-api-facts'
>>> build_api_summary_section(nodes.paragraph("", "Summary")).get("name")
'gp-sphinx-api-summary'
"""

from __future__ import annotations

import typing as t
from dataclasses import dataclass

from docutils import nodes

from sphinx_ux_autodoc_layout._css import API
from sphinx_ux_autodoc_layout._nodes import api_component, build_api_component

_SECTION_KIND_CLASS: dict[str, str] = {
    API.DESCRIPTION: "narrative",
    API.FACTS: "facts",
    API.SUMMARY: "summary",
    API.PARAMETERS: "fields",
    API.OPTIONS: "options",
    API.FOOTER: "members",
}


@dataclass(frozen=True, slots=True)
class ApiFactRow:
    """Typed fact row rendered inside a shared ``gp-sphinx-api-facts`` section.

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
    region_classes = (API.REGION, API.region_modifier(kind)) if kind is not None else ()
    section = build_api_component(name, classes=(*region_classes, *classes))
    for child in children:
        section += child
    return section


def build_api_facts_section(
    rows: t.Sequence[ApiFactRow],
    *,
    classes: tuple[str, ...] = (),
) -> api_component:
    """Render a shared ``gp-sphinx-api-facts`` section from typed fact rows."""
    field_list = nodes.field_list(classes=[API.FACTS_LIST])
    for row in rows:
        field_body = nodes.field_body()
        field_body += row.body
        field_list += nodes.field(
            "",
            nodes.field_name("", row.label),
            field_body,
        )
    return build_api_section(API.FACTS, field_list, classes=classes)


def build_api_table_section(
    name: str,
    *children: nodes.Node,
    classes: tuple[str, ...] = (),
) -> api_component:
    """Wrap one or more table-like body nodes in a shared API section."""
    return build_api_section(name, *children, classes=classes)


def build_api_summary_section(
    *children: nodes.Node,
    classes: tuple[str, ...] = (),
) -> api_component:
    """Wrap summary or index content in the shared ``gp-sphinx-api-summary`` region.

    Parameters
    ----------
    *children : nodes.Node
        Summary or index nodes to render in the shared summary region.
    classes : tuple[str, ...]
        Extra CSS classes appended to the summary wrapper.

    Returns
    -------
    api_component
        Shared summary wrapper.

    Examples
    --------
    >>> from docutils import nodes
    >>> section = build_api_summary_section(nodes.paragraph("", "Summary"))
    >>> section.get("name")
    'gp-sphinx-api-summary'
    """
    return build_api_table_section(API.SUMMARY, *children, classes=classes)
