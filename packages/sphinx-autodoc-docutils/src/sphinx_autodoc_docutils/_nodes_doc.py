"""Rendering directives for custom docutils node documentation."""

from __future__ import annotations

import inspect
import typing as t
from dataclasses import dataclass

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_docutils._badges import build_kind_badge_group
from sphinx_autodoc_docutils._components import (
    component_classes,
    import_component,
    linked_paragraph,
    render_component_nodes,
)
from sphinx_autodoc_docutils._directives import (
    _summary,
    replay_setup,
)
from sphinx_autodoc_docutils.domain import NODE
from sphinx_ux_autodoc_layout import (
    ApiFactRow,
    build_chip_paragraph,
    build_linked_literal,
)

if t.TYPE_CHECKING:
    from sphinx.util.typing import OptionSpec

#: docutils element category mixins surfaced as a fact row, in
#: ``docutils.nodes`` declaration order.
_CATEGORY_MIXINS: tuple[str, ...] = (
    "Root",
    "Titular",
    "PreBibliographic",
    "Bibliographic",
    "Decorative",
    "Structural",
    "Body",
    "General",
    "Sequential",
    "Admonition",
    "Special",
    "Invisible",
    "Part",
    "Inline",
)


@dataclass(frozen=True)
class NodeInfo:
    """Recorded metadata for one documented node class.

    Examples
    --------
    >>> from sphinx_ux_badges import BadgeNode
    >>> info = NodeInfo(cls=BadgeNode, handlers=("html",))
    >>> info.qualified_name
    'sphinx_ux_badges._nodes.BadgeNode'
    >>> info.handlers
    ('html',)
    """

    cls: type[nodes.Element]
    handlers: tuple[str, ...] = ()

    @property
    def qualified_name(self) -> str:
        """Return the fully-qualified dotted path for the class.

        Examples
        --------
        >>> NodeInfo(cls=nodes.paragraph).qualified_name
        'docutils.nodes.paragraph'
        """
        return f"{self.cls.__module__}.{self.cls.__name__}"


def node_categories(cls: type[nodes.Element]) -> list[str]:
    """Return the docutils element categories a node class mixes in.

    Examples
    --------
    >>> node_categories(nodes.image)
    ['Body', 'General', 'Inline']
    >>> node_categories(nodes.note)
    ['Body', 'Admonition']
    """
    return [
        category
        for category in _CATEGORY_MIXINS
        if issubclass(cls, getattr(nodes, category))
    ]


def _nodes_from_calls(
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]],
) -> list[NodeInfo]:
    """Extract node metadata from recorded ``add_node`` calls.

    Handler keyword arguments map builder names to ``(visit, depart)``
    tuples; the ``override`` keyword is registration plumbing, not a
    handler, and is skipped. A repeated registration for the same class
    wins (override semantics).

    Examples
    --------
    >>> def _visit(self, node): ...
    >>> infos = _nodes_from_calls(
    ...     [
    ...         (
    ...             "add_node",
    ...             (nodes.paragraph,),
    ...             {"override": True, "html": (_visit, None)},
    ...         ),
    ...     ],
    ... )
    >>> [(info.cls.__name__, info.handlers) for info in infos]
    [('paragraph', ('html',))]
    """
    by_cls: dict[type[nodes.Element], NodeInfo] = {}
    for call_name, args, kwargs in calls:
        if call_name != "add_node" or len(args) < 1:
            continue
        cls = args[0]
        if not (inspect.isclass(cls) and issubclass(cls, nodes.Element)):
            continue
        handlers = tuple(
            key
            for key, value in kwargs.items()
            if key != "override" and isinstance(value, tuple)
        )
        by_cls[cls] = NodeInfo(cls=cls, handlers=handlers)
    return list(by_cls.values())


def discover_nodes(module_name: str) -> list[NodeInfo]:
    """Return node classes a module defines or registers.

    Combines a module subclass scan with the module's recorded
    ``app.add_node()`` calls, so scanned classes carry their visit /
    depart handler builders and nodes registered from submodules still
    surface. Nodes handled purely by a custom translator (the
    django-docutils ``icon`` pattern, with no ``add_node`` call at all)
    are found by the scan with no handlers.

    Examples
    --------
    >>> infos = discover_nodes("sphinx_ux_badges")
    >>> [(info.cls.__name__, info.handlers) for info in infos]
    [('BadgeNode', ('html',))]

    >>> discover_nodes("sphinx_fonts")
    []
    """
    recorder = replay_setup(module_name)
    registered = _nodes_from_calls(recorder.calls) if recorder is not None else []
    by_cls = {info.cls: info for info in registered}
    infos = [
        by_cls.get(cls, NodeInfo(cls=cls))
        for cls in component_classes(module_name, nodes.Element)
    ]
    scanned = {info.cls for info in infos}
    infos.extend(info for info in registered if info.cls not in scanned)
    return infos


def discover_node(path: str) -> NodeInfo:
    """Return one node class from a fully-qualified dotted path.

    Examples
    --------
    >>> info = discover_node("sphinx_ux_badges.BadgeNode")
    >>> info.cls.__name__
    'BadgeNode'
    """
    cls = t.cast("type[nodes.Element]", import_component(path))
    for info in discover_nodes(cls.__module__):
        if info.cls is cls:
            return info
    return NodeInfo(cls=cls)


def _node_fact_rows(info: NodeInfo) -> list[ApiFactRow]:
    """Return shared fact rows for one autodocumented node.

    Examples
    --------
    >>> rows = _node_fact_rows(NodeInfo(cls=nodes.image, handlers=("html",)))
    >>> [row.label for row in rows]
    ['Python path', 'Base classes', 'Categories', 'Visit/depart handlers']
    """
    base_chips: list[nodes.Node] = [
        build_linked_literal(
            f"{base.__module__}.{base.__qualname__}",
            base.__name__,
        )
        for base in info.cls.__bases__
    ]
    return [
        ApiFactRow("Python path", linked_paragraph(info.qualified_name)),
        ApiFactRow("Base classes", build_chip_paragraph(base_chips)),
        ApiFactRow("Categories", build_chip_paragraph(node_categories(info.cls))),
        ApiFactRow(
            "Visit/depart handlers",
            build_chip_paragraph(list(info.handlers)),
        ),
    ]


def _render_node(
    directive: SphinxDirective,
    info: NodeInfo,
    *,
    no_index: bool = False,
) -> list[nodes.Node]:
    """Render one node entry through the shared component pipeline."""
    return render_component_nodes(
        directive,
        objtype=NODE,
        path=info.qualified_name,
        summary=_summary(info.cls),
        fact_rows=_node_fact_rows(info),
        badge_group=build_kind_badge_group(NODE),
        no_index=no_index,
    )


class AutoNode(SphinxDirective):
    """Render documentation for a single node class."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        info = discover_node(self.arguments[0])
        return _render_node(self, info, no_index="no-index" in self.options)


class AutoNodes(SphinxDirective):
    """Render documentation for every node a module defines or registers."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        no_index = "no-index" in self.options
        results: list[nodes.Node] = []
        for info in discover_nodes(self.arguments[0]):
            results.extend(_render_node(self, info, no_index=no_index))
        return results
