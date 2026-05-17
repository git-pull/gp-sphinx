"""Post-transforms for sphinx_ux_tabs.

The package runs two passes during HTML post-transform:

1. **Grouping pass** — walks the doctree, collects consecutive
   :class:`~sphinx_ux_tabs._nodes.TabContainer` siblings, and folds each
   run into a :class:`~sphinx_ux_tabs._nodes.TabSetNode` whose children
   are :class:`~sphinx_ux_tabs._nodes.TabItemNode` clones of the source
   containers.  A ``:new-set:`` flag on any container forces the run to
   restart at that node.

2. **Expansion pass** — replaces every :class:`TabSetNode` with the
   sequence of ``[TabInputNode, TabLabelNode, panel]`` triples the HTML
   visitors recognise.  Selection follows sphinx-design semantics: the
   first item with ``selected=True`` wins; absent any selected, the
   first item is checked; multiple selected items emit a warning and
   only the first is honoured.

Both passes run inside one :class:`TabsPostTransform.run`.

Examples
--------
>>> TabsPostTransform.default_priority
200

>>> TabsPostTransform.formats
('html',)
"""

from __future__ import annotations

import typing as t

from docutils import nodes
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util.logging import getLogger

from sphinx_ux_tabs._css import SUT
from sphinx_ux_tabs._nodes import (
    TabContainer,
    TabInputNode,
    TabItemNode,
    TabLabelNode,
    TabSetNode,
)

WARNING_TYPE = "gp-sphinx-tabs"

_LOGGER = getLogger(__name__)


def _is_tab_container(node: nodes.Node) -> bool:
    """Return ``True`` when ``node`` is a :class:`TabContainer`.

    Examples
    --------
    >>> _is_tab_container(TabContainer())
    True

    >>> from docutils import nodes
    >>> _is_tab_container(nodes.paragraph())
    False
    """
    return isinstance(node, TabContainer)


def _tab_container_to_tab_item(container: TabContainer) -> TabItemNode:
    """Convert a :class:`TabContainer` into a :class:`TabItemNode`.

    The original ``[label, panel]`` children are detached from the
    source container and re-parented onto the new :class:`TabItemNode`.
    The ``selected`` flag is carried across.

    Parameters
    ----------
    container : TabContainer
        The source container.  Its children must be ``[label, panel]``.

    Returns
    -------
    TabItemNode
        A new tab item carrying the same children and ``selected`` flag.

    Examples
    --------
    >>> from docutils import nodes
    >>> tc = TabContainer(selected=True)
    >>> tc += nodes.label("", "Python")
    >>> tc += nodes.container("", nodes.paragraph("", "body"), is_div=True)
    >>> item = _tab_container_to_tab_item(tc)
    >>> isinstance(item, TabItemNode), item["selected"]
    (True, True)

    >>> len(item.children)
    2
    """
    item = TabItemNode(selected=container.get("selected", False))
    # Detach children — list copy so we can mutate during iteration.
    for child in list(container.children):
        container.remove(child)
        item += child
    return item


def _group_tab_containers(document: nodes.document) -> None:
    """Fold each run of consecutive :class:`TabContainer` siblings into a set.

    Walks every parent that owns a :class:`TabContainer` child and
    rewrites that parent's children so each maximal run of consecutive
    containers (modulo ``:new-set:`` breaks) becomes a single
    :class:`TabSetNode`.

    Parameters
    ----------
    document : nodes.document
        The doctree to mutate in place.

    Examples
    --------
    >>> from docutils import nodes
    >>> from docutils.utils import new_document
    >>> from docutils.frontend import OptionParser
    >>> from docutils.parsers.rst import Parser
    >>> doc = new_document(
    ...     "<t>",
    ...     OptionParser(components=(Parser,)).get_default_values(),
    ... )
    >>> tc1 = TabContainer()
    >>> tc1 += nodes.label("", "A")
    >>> tc1 += nodes.container("", is_div=True)
    >>> doc += tc1
    >>> _group_tab_containers(doc)
    >>> isinstance(doc.children[0], TabSetNode)
    True
    """
    # Collect every distinct parent that owns at least one TabContainer.
    parents: list[nodes.Element] = []
    seen: set[int] = set()
    for tc in document.findall(TabContainer):
        parent = tc.parent
        if parent is None:
            continue
        if id(parent) in seen:
            continue
        seen.add(id(parent))
        parents.append(parent)

    for parent in parents:
        _rewrite_parent(parent)


def _rewrite_parent(parent: nodes.Element) -> None:
    """Replace consecutive TabContainer runs in ``parent`` with TabSetNodes.

    Mutates ``parent.children`` in place.

    Parameters
    ----------
    parent : nodes.Element
        The parent element to rewrite.
    """
    new_children: list[nodes.Node] = []
    run: list[TabContainer] = []

    def flush_run() -> None:
        if not run:
            return
        tab_set = TabSetNode()
        # Carry source-line info from the first container so that warnings
        # the expansion pass emits point at the source location.
        tab_set.source = run[0].source
        tab_set.line = run[0].line
        tab_set.parent = parent
        for container in run:
            item = _tab_container_to_tab_item(container)
            item.source = container.source
            item.line = container.line
            tab_set += item
        new_children.append(tab_set)
        run.clear()

    for child in parent.children:
        if isinstance(child, TabContainer):
            if child.get("new_set", False) and run:
                flush_run()
            run.append(child)
        else:
            flush_run()
            new_children.append(child)
    flush_run()

    parent.children = new_children
    for child in parent.children:
        child.parent = parent


def _expand_tab_sets(document: nodes.document) -> None:
    """Expand every :class:`TabSetNode` into ``[input, label, panel]`` triples.

    Each :class:`TabSetNode` is mutated in place: its existing
    :class:`TabItemNode` children are replaced with a flat sequence of
    ``[TabInputNode, TabLabelNode, panel]`` for each tab.  The expansion
    pass also picks the initially-checked tab using sphinx-design's
    selection precedence.

    Parameters
    ----------
    document : nodes.document
        The doctree to mutate in place.

    Examples
    --------
    >>> from docutils import nodes
    >>> from docutils.utils import new_document
    >>> from docutils.frontend import OptionParser
    >>> from docutils.parsers.rst import Parser
    >>> doc = new_document(
    ...     "<t>",
    ...     OptionParser(components=(Parser,)).get_default_values(),
    ... )
    >>> ts = TabSetNode()
    >>> ti = TabItemNode()
    >>> ti += nodes.label("", "A")
    >>> ti += nodes.container("", is_div=True)
    >>> ts += ti
    >>> doc += ts
    >>> _expand_tab_sets(doc)
    >>> isinstance(ts.children[0], TabInputNode)
    True
    >>> ts.children[0]["checked"]
    True
    """
    # Snapshot the list — we mutate the children of each tab set in place,
    # but enumerate gives stable indexes for set_name/input_id generation.
    tab_sets = list(document.findall(TabSetNode))
    for set_index, tab_set in enumerate(tab_sets):
        _expand_one_tab_set(tab_set, set_index)


def _expand_one_tab_set(tab_set: TabSetNode, set_index: int) -> None:
    """Expand a single :class:`TabSetNode` in place.

    Parameters
    ----------
    tab_set : TabSetNode
        The tab-set node whose :class:`TabItemNode` children are
        replaced with the radio-input expansion.
    set_index : int
        Document-wide tab-set counter (used to build the radio group
        name and tab-item ids).
    """
    items: list[TabItemNode] = [
        child for child in tab_set.children if isinstance(child, TabItemNode)
    ]
    if not items:
        return

    set_name = SUT.set_name(set_index)
    selected_idx = _resolve_selected_index(items)

    new_children: list[nodes.Node] = []
    for item_index, item in enumerate(items):
        if len(item.children) != 2:
            _LOGGER.warning(
                "malformed tab-item: expected 2 children, got %d [%s.tab]",
                len(item.children),
                WARNING_TYPE,
                location=item,
                type=WARNING_TYPE,
                subtype="tab",
            )
            continue
        label_src, panel = item.children
        if not isinstance(label_src, nodes.Element) or not isinstance(
            panel, nodes.Element
        ):
            _LOGGER.warning(
                "tab-item children are not Element nodes [%s.tab]",
                WARNING_TYPE,
                location=item,
                type=WARNING_TYPE,
                subtype="tab",
            )
            continue
        input_id = SUT.input_id(set_index, item_index)

        input_node = TabInputNode(
            input_id=input_id,
            set_name=set_name,
            checked=(item_index == selected_idx),
        )
        input_node.source = item.source
        input_node.line = item.line
        new_children.append(input_node)

        # Label preserves the text-children of the original label so any
        # inline markup the author wrote (e.g. ``:bash:`` literal) survives.
        label_children = list(label_src.children)
        label_node = TabLabelNode(
            "",
            "",
            *label_children,
            input_id=input_id,
            sync_id=item.get("sync_id", ""),
            sync_group=item.get("sync_group", ""),
        )
        # Preserve cross-reference anchors registered via ``add_name`` on the
        # source label — the label is the node Sphinx's StandardDomain points
        # ``{ref}`` resolution at.
        label_node["ids"] = list(label_src.get("ids", []))
        label_node["names"] = list(label_src.get("names", []))
        label_node.source = item.source
        label_node.line = item.line
        new_children.append(label_node)

        # Panel: detach from the source item, then re-parent.  Tag with the
        # panel namespace class so the CSS selectors can target it.
        panel_classes = list(panel.get("classes", []))
        if SUT.PANEL not in panel_classes:
            panel_classes.append(SUT.PANEL)
        panel["classes"] = panel_classes
        new_children.append(panel)

    tab_set.children = []
    for child in new_children:
        tab_set += child


def _resolve_selected_index(items: list[TabItemNode]) -> int:
    """Pick the index of the initially-checked tab.

    Selection precedence:

    1. The first item with ``selected=True`` wins.
    2. Absent any selected item, index ``0`` is chosen.
    3. Multiple selected items emit a warning; only the first wins.

    Parameters
    ----------
    items : list[TabItemNode]
        The tab items (already filtered to :class:`TabItemNode`).

    Returns
    -------
    int
        The index of the initially-checked tab.

    Examples
    --------
    >>> _resolve_selected_index([TabItemNode(), TabItemNode()])
    0

    >>> _resolve_selected_index([TabItemNode(), TabItemNode(selected=True)])
    1
    """
    selected_idx: int | None = None
    for idx, item in enumerate(items):
        if not item.get("selected", False):
            continue
        if selected_idx is None:
            selected_idx = idx
        else:
            _LOGGER.warning(
                "multiple selected tab items in one tab-set [%s.tab]",
                WARNING_TYPE,
                location=item,
                type=WARNING_TYPE,
                subtype="tab",
            )
    return 0 if selected_idx is None else selected_idx


class TabsPostTransform(SphinxPostTransform):
    """Two-pass post-transform: group consecutive tabs, then expand to HTML.

    Runs only for HTML builders — other output formats fall back to the
    default container rendering of :class:`TabSetNode` /
    :class:`TabItemNode`, which is correct (label + body).

    Examples
    --------
    >>> TabsPostTransform.default_priority
    200

    >>> "html" in TabsPostTransform.formats
    True
    """

    default_priority = 200
    formats = ("html",)

    def run(self, **kwargs: t.Any) -> None:
        """Run both passes on the post-transform document.

        Examples
        --------
        >>> TabsPostTransform.run.__qualname__
        'TabsPostTransform.run'
        """
        del kwargs
        _group_tab_containers(self.document)
        _expand_tab_sets(self.document)


__all__ = [
    "WARNING_TYPE",
    "TabsPostTransform",
]
