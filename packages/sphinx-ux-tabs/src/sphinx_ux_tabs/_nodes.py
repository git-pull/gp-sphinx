"""Custom docutils nodes for sphinx_ux_tabs.

The package defines six custom nodes covering both the authoring-time
shape and the expanded HTML-ready shape:

* :class:`TabContainer` — emitted by the ``.. tab::`` directive.  Holds
  ``[label, panel]`` children and is replaced by the post-transform.
* :class:`TabSetNode` — the persistent container that wraps a tab set's
  ``[input, label, panel]`` triples in the final tree.
* :class:`TabItemNode` — emitted by ``.. tab-set::`` / ``.. tab-item::``
  for the sphinx-design-compatible authoring style.  Holds the same
  ``[label, panel]`` children as :class:`TabContainer` but does not
  participate in the consecutive-sibling grouping pass.
* :class:`TabInputNode` — void HTML ``<input type="radio">``.
* :class:`TabLabelNode` — ``<label for="...">`` text element.
* :class:`TabPanelNode` — ``<div class="gp-sphinx-tabs__panel">``
  wrapping a single tab's body content.  Carries the sync attributes
  and any ``:class-container:`` classes so CSS attribute selectors and
  prehydrate restore can address it.

Examples
--------
>>> from docutils import nodes
>>> tc = TabContainer(new_set=False)
>>> tc["new_set"]
False

>>> ts = TabSetNode()
>>> 'gp-sphinx-tabs' in ts["classes"]
True

>>> ti = TabItemNode(selected=True)
>>> ti["selected"]
True

>>> inp = TabInputNode(input_id="x", set_name="g", checked=True)
>>> inp["input_id"], inp["checked"]
('x', True)

>>> lbl = TabLabelNode("", "Hello", input_id="x")
>>> lbl.astext()
'Hello'
"""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_ux_tabs._css import SUT


class TabContainer(nodes.container):
    """Transient container emitted by ``.. tab::``.

    Children are ``[label, panel]``.  This node is consumed by the
    grouping pass of :class:`~sphinx_ux_tabs._transforms.TabsPostTransform`
    and never reaches the final doctree.

    Parameters
    ----------
    new_set : bool, optional
        Whether ``:new-set:`` was set on the source directive — forces
        the grouping pass to start a fresh :class:`TabSetNode` even when
        this container is a sibling of another :class:`TabContainer`.
    selected : bool, optional
        Whether ``:selected:`` was set on the source directive (carried
        through into :class:`TabItemNode` during expansion).

    Examples
    --------
    >>> tc = TabContainer()
    >>> tc["new_set"], tc["selected"]
    (False, False)

    >>> tc2 = TabContainer(new_set=True, selected=True)
    >>> tc2["new_set"], tc2["selected"]
    (True, True)
    """

    def __init__(
        self,
        rawsource: str = "",
        *children: nodes.Node,
        new_set: bool = False,
        selected: bool = False,
        **attributes: t.Any,
    ) -> None:
        super().__init__(rawsource, *children, **attributes)
        self["new_set"] = new_set
        self["selected"] = selected
        self["is_div"] = True


class TabSetNode(nodes.container):
    """Persistent tab-set container — wraps ``[input, label, panel]`` triples.

    After the grouping pass, every tab set is materialised as a
    :class:`TabSetNode`.  Its children alternate input → label → panel
    until the expansion pass replaces it with the same triples directly.

    Examples
    --------
    >>> ts = TabSetNode()
    >>> 'gp-sphinx-tabs' in ts["classes"]
    True

    >>> ts["is_div"]
    True
    """

    def __init__(
        self,
        rawsource: str = "",
        *children: nodes.Node,
        classes: list[str] | None = None,
        **attributes: t.Any,
    ) -> None:
        super().__init__(rawsource, *children, **attributes)
        if SUT.TABS not in self["classes"]:
            self["classes"].insert(0, SUT.TABS)
        if classes:
            for c in classes:
                if c and c not in self["classes"]:
                    self["classes"].append(c)
        self["is_div"] = True


class TabItemNode(nodes.container):
    """A single tab item — holds ``[label, panel]`` children.

    Emitted by ``.. tab-item::`` (sphinx-design style) and also by the
    grouping pass when it folds a run of :class:`TabContainer` siblings
    into a :class:`TabSetNode`.

    Parameters
    ----------
    selected : bool, optional
        Whether ``:selected:`` was set on the source directive — the
        expansion pass uses the first selected tab as the initially
        checked radio.
    sync_id : str, optional
        Optional sync group id (sphinx-design ``:sync:`` semantics).
        Surfaced as a ``data-sync-id`` attribute on the rendered label
        and panel.
    class_container : list[str], optional
        Extra CSS classes to apply to the rendered panel container —
        the ``:class-container:`` option on ``.. tab-item::``.

    Examples
    --------
    >>> ti = TabItemNode()
    >>> ti["selected"], ti["sync_id"], ti["class_container"]
    (False, '', [])

    >>> ti2 = TabItemNode(selected=True, sync_id="lang")
    >>> ti2["selected"], ti2["sync_id"]
    (True, 'lang')

    >>> ti3 = TabItemNode(class_container=["my-callout"])
    >>> ti3["class_container"]
    ['my-callout']
    """

    def __init__(
        self,
        rawsource: str = "",
        *children: nodes.Node,
        selected: bool = False,
        sync_id: str = "",
        class_container: list[str] | None = None,
        **attributes: t.Any,
    ) -> None:
        super().__init__(rawsource, *children, **attributes)
        self["selected"] = selected
        self["sync_id"] = sync_id
        self["class_container"] = list(class_container) if class_container else []
        self["is_div"] = True


class TabInputNode(nodes.Element):
    """Void ``<input type="radio">`` — one per tab.

    Carries the ``input_id``, ``set_name``, and ``checked`` attributes
    the HTML visitor reads when emitting the opening tag.  The node is
    void: nothing is emitted on departure.

    Examples
    --------
    >>> inp = TabInputNode(input_id="x", set_name="g")
    >>> inp["input_id"], inp["set_name"], inp["checked"]
    ('x', 'g', False)

    >>> inp2 = TabInputNode(input_id="y", set_name="g", checked=True)
    >>> inp2["checked"]
    True
    """

    def __init__(
        self,
        rawsource: str = "",
        *,
        input_id: str = "",
        set_name: str = "",
        checked: bool = False,
        classes: list[str] | None = None,
        **attributes: t.Any,
    ) -> None:
        super().__init__(rawsource, **attributes)
        self["input_id"] = input_id
        self["set_name"] = set_name
        self["checked"] = checked
        if SUT.INPUT not in self["classes"]:
            self["classes"].insert(0, SUT.INPUT)
        if classes:
            for c in classes:
                if c and c not in self["classes"]:
                    self["classes"].append(c)


class TabLabelNode(nodes.TextElement):
    """``<label for="...">`` carrying the tab's title nodes.

    Subclasses :class:`docutils.nodes.TextElement` so unregistered
    builders fall back to ``visit_inline`` via Sphinx's MRO dispatch.

    Parameters
    ----------
    input_id : str
        The DOM id of the matching :class:`TabInputNode` — emitted as
        the ``for=`` attribute.
    sync_id : str, optional
        Optional sync-group id (``data-sync-id`` attribute).
    sync_group : str, optional
        Optional sync-group name (``data-sync-group`` attribute) — the
        tab-set's ``:sync-group:`` option resolved during expansion.

    Examples
    --------
    >>> lbl = TabLabelNode("", "Python", input_id="x")
    >>> lbl.astext()
    'Python'

    >>> lbl["input_id"]
    'x'

    >>> lbl2 = TabLabelNode("", "Bash", input_id="y", sync_group="shell")
    >>> lbl2["sync_group"]
    'shell'
    """

    def __init__(
        self,
        rawsource: str = "",
        text: str = "",
        *children: nodes.Node,
        input_id: str = "",
        sync_id: str = "",
        sync_group: str = "",
        classes: list[str] | None = None,
        **attributes: t.Any,
    ) -> None:
        super().__init__(rawsource, text, *children, **attributes)
        self["input_id"] = input_id
        self["sync_id"] = sync_id
        self["sync_group"] = sync_group
        if SUT.LABEL not in self["classes"]:
            self["classes"].insert(0, SUT.LABEL)
        if classes:
            for c in classes:
                if c and c not in self["classes"]:
                    self["classes"].append(c)


class TabPanelNode(nodes.container):
    """The ``<div class="gp-sphinx-tabs__panel">`` wrapping one tab body.

    The expansion pass re-parents the source ``.. tab-item::`` panel's
    children onto this node so the HTML visitor can emit
    ``data-sync-id`` / ``data-sync-group`` attributes that CSS attribute
    selectors and the prehydrate restore path can address.  Always
    carries :data:`~sphinx_ux_tabs._css.SUT.PANEL` in ``classes`` —
    extra ``:class-container:`` classes are appended.

    Parameters
    ----------
    sync_id : str, optional
        Mirrors the parent tab item's ``sync_id`` so the panel can be
        addressed by attribute selector ``[data-sync-id="bash"]``.
    sync_group : str, optional
        Mirrors the parent tab set's resolved ``sync_group``.
    classes : list[str], optional
        Initial CSS classes; the panel class is inserted at the front.

    Examples
    --------
    >>> p = TabPanelNode()
    >>> 'gp-sphinx-tabs__panel' in p["classes"]
    True

    >>> p2 = TabPanelNode(sync_id="bash", sync_group="shell")
    >>> p2["sync_id"], p2["sync_group"]
    ('bash', 'shell')
    """

    def __init__(
        self,
        rawsource: str = "",
        *children: nodes.Node,
        sync_id: str = "",
        sync_group: str = "",
        classes: list[str] | None = None,
        **attributes: t.Any,
    ) -> None:
        super().__init__(rawsource, *children, **attributes)
        if SUT.PANEL not in self["classes"]:
            self["classes"].insert(0, SUT.PANEL)
        if classes:
            for c in classes:
                if c and c not in self["classes"]:
                    self["classes"].append(c)
        self["sync_id"] = sync_id
        self["sync_group"] = sync_group
        self["is_div"] = True


__all__ = [
    "TabContainer",
    "TabInputNode",
    "TabItemNode",
    "TabLabelNode",
    "TabPanelNode",
    "TabSetNode",
]
