"""Custom docutils nodes and builders for autodoc layout components.

The extension keeps Sphinx's outer ``dl / dt / dd`` structure but
builds an explicit API component tree within those nodes.

All nodes use the ``api_*`` prefix for the stable DOM contract:
structural wrappers (``api_component``, ``api_slot``, ``api_permalink``),
disclosure widgets (``api_fold``, ``api_sig_fold``), and the legacy
region wrapper (``api_region``).

Examples
--------
>>> from sphinx_ux_autodoc_layout._nodes import (
...     api_component,
...     build_api_component,
...     api_fold,
... )
>>> comp = api_component(name="api-layout", tag="div")
>>> comp.get("name")
'api-layout'

>>> built = build_api_component("api-content", classes=("demo",))
>>> built.get("classes")
['api-content', 'demo']

>>> fold = api_fold(kind="parameters", summary="Parameters (5)")
>>> fold.get("summary")
'Parameters (5)'
"""

from __future__ import annotations

import typing as t

from docutils import nodes

APISlotName = t.Literal["badges", "source-link"]
"""Stable slot names used to hand structured header content to layout."""


class api_region(nodes.General, nodes.Element):
    """Legacy wrapper for a contiguous ``desc_content`` run.

    Parameters
    ----------
    kind : str
        One of ``"narrative"``, ``"fields"``, or ``"members"``.

    Examples
    --------
    >>> r = api_region(kind="narrative")
    >>> isinstance(r, api_region)
    True
    >>> r.get("kind")
    'narrative'
    """


class api_fold(nodes.General, nodes.Element):
    """Block disclosure wrapper rendered as ``<details>/<summary>``.

    Parameters
    ----------
    kind : str
        Fold category, e.g. ``"parameters"``.
    summary : str
        Text shown in the ``<summary>`` element.
    open : bool
        Whether the fold starts expanded.

    Examples
    --------
    >>> f = api_fold(kind="parameters", summary="Parameters (3)")
    >>> f.get("kind")
    'parameters'
    >>> f.get("summary")
    'Parameters (3)'
    """


class api_component(nodes.General, nodes.Element):
    """Generic API wrapper node with a stable component name.

    Parameters
    ----------
    name : str
        Stable DOM contract name such as ``"api-layout"``.
    tag : str
        HTML tag to emit. Defaults to ``"div"``.

    Examples
    --------
    >>> node = api_component(name="api-content", tag="div")
    >>> node.get("name")
    'api-content'
    >>> node.get("tag")
    'div'
    """


class api_inline_component(nodes.General, nodes.Inline, nodes.TextElement):
    """Inline API wrapper node for text-compatible header components.

    Parameters
    ----------
    name : str
        Stable DOM contract name such as ``"api-source-link"``.
    tag : str
        HTML tag to emit. Defaults to ``"span"``.

    Examples
    --------
    >>> node = api_inline_component(name="api-source-link", tag="span")
    >>> node.get("name")
    'api-source-link'
    """


class api_slot(nodes.General, nodes.Element):
    """Structural slot marker consumed by the layout transform.

    Parameters
    ----------
    slot : APISlotName
        Slot name such as ``"badges"`` or ``"source-link"``.

    Examples
    --------
    >>> slot = api_slot(slot="badges")
    >>> slot.get("slot")
    'badges'
    """


class api_permalink(nodes.General, nodes.Element):
    """Permalink anchor rendered inside ``api-layout-left``.

    Parameters
    ----------
    href : str
        Fragment link target such as ``"#mod.func"``.
    title : str
        Link title shown on hover.

    Examples
    --------
    >>> link = api_permalink(href="#mod.func", title="Link to this definition")
    >>> link.get("href")
    '#mod.func'
    """


class api_sig_fold(nodes.General, nodes.Element):
    """Inline signature disclosure toggle for large parameter lists.

    The preview button lives in the signature row, while the expanded
    multiline signature content is rendered in a controlled wrapper
    inside ``api-signature``.

    Parameters
    ----------
    first_param : str
        Text of the first parameter shown in collapsed preview.
    param_count : int
        Total number of parameters.
    panel_id : str
        DOM id of the controlled expanded signature wrapper.

    Examples
    --------
    >>> sf = api_sig_fold(first_param="host", param_count=13, panel_id="sig-panel")
    >>> sf.get("first_param")
    'host'
    >>> sf.get("param_count")
    13
    >>> sf.get("panel_id")
    'sig-panel'
    """


def build_api_component(
    name: str,
    *,
    tag: str = "div",
    classes: tuple[str, ...] = (),
    html_attrs: dict[str, str] | None = None,
) -> api_component:
    """Create an ``api_component`` with stable DOM classes.

    Parameters
    ----------
    name : str
        Stable DOM contract name such as ``"api-layout"``.
    tag : str
        HTML tag emitted by the visitor.
    classes : tuple[str, ...]
        Additional compatibility classes.
    html_attrs : dict[str, str] | None
        Extra HTML attributes for the rendered tag.

    Returns
    -------
    api_component
        A configured component wrapper.

    Examples
    --------
    >>> wrapper = build_api_component("api-content", classes=("legacy",))
    >>> wrapper.get("classes")
    ['api-content', 'legacy']
    """
    component = api_component(name=name, tag=tag)
    component["classes"] = [name, *classes]
    if html_attrs:
        component["html_attrs"] = html_attrs
    return component


def build_api_inline_component(
    name: str,
    *,
    tag: str = "span",
    classes: tuple[str, ...] = (),
    html_attrs: dict[str, str] | None = None,
) -> api_inline_component:
    """Create an inline API wrapper for text-compatible header content.

    Parameters
    ----------
    name : str
        Stable DOM contract name such as ``"api-source-link"``.
    tag : str
        HTML tag emitted by the visitor.
    classes : tuple[str, ...]
        Additional compatibility classes.
    html_attrs : dict[str, str] | None
        Extra HTML attributes for the rendered tag.

    Returns
    -------
    api_inline_component
        A configured inline component wrapper.
    """
    component = api_inline_component(name=name, tag=tag)
    component["classes"] = [name, *classes]
    if html_attrs:
        component["html_attrs"] = html_attrs
    return component


def build_api_slot(
    slot_name: APISlotName,
    *children: nodes.Node,
    classes: tuple[str, ...] = (),
) -> api_slot:
    """Create an ``api_slot`` with a stable slot-specific class name.

    Parameters
    ----------
    slot_name : APISlotName
        Slot name for the contained content.
    *children : nodes.Node
        Child nodes to place in the slot.
    classes : tuple[str, ...]
        Additional compatibility classes.

    Returns
    -------
    api_slot
        A configured slot marker node.

    Examples
    --------
    >>> slot = build_api_slot("badges", nodes.inline("", "demo"))
    >>> slot.get("classes")
    ['api-slot', 'api-slot--badges']
    >>> slot.astext()
    'demo'
    """
    slot = api_slot(slot=slot_name)
    slot["classes"] = ["api-slot", f"api-slot--{slot_name}", *classes]
    for child in children:
        slot += child
    return slot
