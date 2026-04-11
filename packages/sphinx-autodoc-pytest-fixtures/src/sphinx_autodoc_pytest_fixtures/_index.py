"""Index table generation helpers for sphinx_autodoc_pytest_fixtures."""

from __future__ import annotations

import typing as t

from docutils import nodes
from sphinx import addnodes
from sphinx.util import logging as sphinx_logging
from sphinx.util.nodes import make_refnode
from sphinx_autodoc_layout import build_api_summary_section
from sphinx_typehints_gp import build_resolved_annotation_paragraph

from sphinx_autodoc_pytest_fixtures._badges import _build_badge_group_node
from sphinx_autodoc_pytest_fixtures._constants import (
    _INDEX_TABLE_COLUMNS,
    _RST_INLINE_PATTERN,
)

_FIXTURE_INDEX = "spf-fixture-index"
_TABLE_SCROLL = "spf-table-scroll"

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.domains.python import PythonDomain

    from sphinx_autodoc_pytest_fixtures._models import (
        FixtureMeta,
        autofixture_index_node,
    )
    from sphinx_autodoc_pytest_fixtures._store import FixtureStoreDict

logger = sphinx_logging.getLogger(__name__)


def _parse_rst_inline(
    text: str,
    app: Sphinx,
    docname: str,
) -> list[nodes.Node]:
    """Parse RST inline markup into doctree nodes with resolved cross-refs.

    Handles ``:class:`Target```, ``:fixture:`name```, ````literal````,
    and plain text.  Cross-references are created as ``pending_xref`` nodes
    and resolved via ``env.resolve_references()``.

    Parameters
    ----------
    text : str
        RST inline text, e.g. ``"Return new :class:`libtmux.Server`."``.
    app : Sphinx
        The Sphinx application (for builder and env access).
    docname : str
        Current document name (for relative URI resolution).

    Returns
    -------
    list[nodes.Node]
        Sequence of text, literal, and reference nodes ready for insertion.
    """
    result_nodes: list[nodes.Node] = []

    # Tokenise: :role:`content`, ``literal``, or plain text
    pattern = _RST_INLINE_PATTERN
    pos = 0
    for m in pattern.finditer(text):
        # Plain text before match
        if m.start() > pos:
            result_nodes.append(nodes.Text(text[pos : m.start()]))

        if m.group(1):
            # :role:`content` — build a pending_xref
            role = m.group(1)
            content = m.group(2)

            # Handle ~ shortening prefix
            if content.startswith("~"):
                target = content[1:]
                display = target.rsplit(".", 1)[-1]
            elif "<" in content and ">" in content:
                display = content.split("<")[0].strip()
                target = content.split("<")[1].rstrip(">").strip()
            else:
                target = content
                display = content.rsplit(".", 1)[-1]

            xref = addnodes.pending_xref(
                "",
                nodes.literal(display, display, classes=["xref", "py", f"py-{role}"]),
                refdomain="py",
                reftype=role,
                reftarget=target,
                refexplicit=True,
                refwarn=True,
            )
            xref["refdoc"] = docname
            result_nodes.append(xref)

        elif m.group(3):
            # ``literal`` — inline code
            result_nodes.append(nodes.literal(m.group(3), m.group(3), classes=["code"]))
        elif m.group(4):
            # `interpreted text` — render as inline code (Sphinx default role
            # in the Python domain is :obj:, which renders as code)
            result_nodes.append(nodes.literal(m.group(4), m.group(4)))

        pos = m.end()

    # Trailing plain text
    if pos < len(text):
        result_nodes.append(nodes.Text(text[pos:]))

    # Resolve pending_xref nodes via env.resolve_references
    if any(isinstance(n, addnodes.pending_xref) for n in result_nodes):
        from sphinx.util.docutils import new_document

        temp_doc = new_document("<autofixture-index>")
        temp_para = nodes.paragraph()
        for n in result_nodes:
            temp_para += n
        temp_doc += temp_para
        app.env.resolve_references(temp_doc, docname, app.builder)
        # Extract resolved nodes from the temp paragraph
        result_nodes = list(temp_para.children)

    return result_nodes


def _select_fixture_index_fixtures(
    store: FixtureStoreDict,
    modname: str,
    exclude: set[str],
) -> list[FixtureMeta]:
    """Return fixture metadata that should appear in the generated index."""
    return [
        meta
        for canon, meta in sorted(store["fixtures"].items())
        if canon.startswith(f"{modname}.") and meta.public_name not in exclude
    ]


def _build_fixture_index_table_structure(
    fixtures: list[FixtureMeta],
) -> tuple[nodes.table, nodes.tbody]:
    """Return the index table shell populated with plain fixture metadata."""
    table = nodes.table(classes=[_FIXTURE_INDEX])
    tgroup = nodes.tgroup(cols=len(_INDEX_TABLE_COLUMNS))
    table += tgroup
    for _header, width in _INDEX_TABLE_COLUMNS:
        tgroup += nodes.colspec(colwidth=width)

    thead = nodes.thead()
    tgroup += thead
    header_row = nodes.row()
    thead += header_row
    for header, _width in _INDEX_TABLE_COLUMNS:
        entry = nodes.entry()
        entry += nodes.paragraph("", header)
        header_row += entry

    tbody = nodes.tbody()
    tgroup += tbody
    for meta in fixtures:
        row = nodes.row()
        tbody += row

        name_entry = nodes.entry()
        name_entry += nodes.paragraph(
            "",
            "",
            nodes.literal(meta.public_name, meta.public_name),
        )
        row += name_entry

        flags_entry = nodes.entry()
        flags_para = nodes.paragraph()
        flags_para += _build_badge_group_node(
            scope=meta.scope,
            kind=meta.kind,
            autouse=meta.autouse,
            deprecated=bool(meta.deprecated),
            show_fixture_badge=True,
        )
        flags_entry += flags_para
        row += flags_entry

        ret_entry = nodes.entry()
        ret_entry += nodes.paragraph("", meta.return_display)
        row += ret_entry

        desc_entry = nodes.entry()
        desc_entry += nodes.paragraph("", meta.summary)
        row += desc_entry

    return table, tbody


def _resolve_fixture_index(
    node: autofixture_index_node,
    store: FixtureStoreDict,
    py_domain: PythonDomain,
    app: Sphinx,
    docname: str,
) -> None:
    """Replace a :class:`autofixture_index_node` with a docutils table.

    Builds a 4-column table (Fixture, Flags, Returns, Description).
    Scope, kind, autouse, and deprecated appear as badges in the Flags column.
    Fixture names and return types are cross-referenced; description text
    has RST inline markup parsed and rendered.

    Parameters
    ----------
    node : autofixture_index_node
        The placeholder node to replace.
    store : FixtureStoreDict
        The finalized fixture store.
    py_domain : PythonDomain
        Python domain for cross-reference resolution.
    app : Sphinx
        The Sphinx application.
    docname : str
        Current document name.
    """
    modname = node["module"]
    exclude: set[str] = node.get("exclude", set())

    fixtures = _select_fixture_index_fixtures(store, modname, exclude)

    if not fixtures:
        node.replace_self([])
        return

    table, tbody = _build_fixture_index_table_structure(fixtures)
    for meta, row_node in zip(fixtures, tbody.children, strict=True):
        row = t.cast(nodes.row, row_node)
        name_entry, _flags_entry, ret_entry, desc_entry = t.cast(
            tuple[nodes.entry, nodes.entry, nodes.entry, nodes.entry],
            tuple(row.children),
        )

        # --- Fixture name: cross-ref link ---
        obj_entry = py_domain.objects.get(meta.canonical_name)
        if obj_entry is not None:
            ref_node: nodes.Node = make_refnode(
                app.builder,
                docname,
                obj_entry.docname,
                obj_entry.node_id,
                nodes.literal(meta.public_name, meta.public_name),
            )
        else:
            ref_node = nodes.literal(meta.public_name, meta.public_name)
        name_para = nodes.paragraph()
        name_para += ref_node
        name_entry[:] = [name_para]

        # --- Returns: linked type name ---
        ret_entry[:] = [
            build_resolved_annotation_paragraph(
                meta.return_display,
                app,
                docname,
            )
        ]

        # --- Description: parsed RST inline markup ---
        desc_para = nodes.paragraph()
        if meta.summary:
            for desc_node in _parse_rst_inline(meta.summary, app, docname):
                desc_para += desc_node
        desc_entry[:] = [desc_para]

    scroll_wrapper = nodes.container(classes=[_TABLE_SCROLL])
    scroll_wrapper += table
    node.replace_self([build_api_summary_section(scroll_wrapper)])
