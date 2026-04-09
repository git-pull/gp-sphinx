"""Shared helpers for reparsing generated Sphinx object markup.

Examples
--------
>>> from docutils import nodes
>>> from docutils.statemachine import StringList
>>> class DummyState:
...     def nested_parse(
...         self,
...         view_list: StringList,
...         offset: int,
...         node: nodes.Element,
...     ) -> None:
...         for line in view_list:
...             node += nodes.paragraph("", line)
>>> class DummyDirective:
...     state = DummyState()
...     content_offset = 0
...     def get_source_info(self) -> tuple[str, int]:
...         return ("demo.md", 1)
>>> rendered = parse_generated_markup(
...     DummyDirective(),
...     "demo",
... )  # type: ignore[arg-type]
>>> rendered[0].astext()
'demo'
"""

from __future__ import annotations

import typing as t

from docutils import nodes
from docutils.statemachine import StringList
from sphinx import addnodes

if t.TYPE_CHECKING:
    from sphinx.util.docutils import SphinxDirective


def parse_generated_markup(
    directive: SphinxDirective,
    markup: str,
) -> list[nodes.Node]:
    """Parse generated markup through Sphinx when available.

    Parameters
    ----------
    directive : SphinxDirective
        Directive requesting nested parsing.
    markup : str
        Generated reStructuredText or MyST markup to parse.

    Returns
    -------
    list[nodes.Node]
        Parsed nodes ready for further normalization.
    """
    if hasattr(directive, "parse_text_to_nodes"):
        return directive.parse_text_to_nodes(markup)

    source, _line = directive.get_source_info()
    view_list: StringList = StringList()
    for line in markup.splitlines():
        view_list.append(line, source)
    container = nodes.container()
    directive.state.nested_parse(view_list, directive.content_offset, container)
    return [container] if container.children else []


def iter_desc_nodes(node_list: list[nodes.Node]) -> t.Iterator[addnodes.desc]:
    """Yield ``addnodes.desc`` nodes from parsed markup.

    Parameters
    ----------
    node_list : list[nodes.Node]
        Parsed nodes returned by :func:`parse_generated_markup`.

    Yields
    ------
    addnodes.desc
        Description nodes found anywhere inside ``node_list``.
    """
    for node in node_list:
        yield from node.findall(addnodes.desc)
