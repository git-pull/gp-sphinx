"""Custom docutils nodes for autodoc layout components.

The extension keeps Sphinx's outer ``dl / dt / dd`` structure but
builds an explicit API component tree within those nodes.

Examples
--------
>>> from sphinx_autodoc_layout._nodes import api_component, gal_fold
>>> comp = api_component(name="api-layout", tag="div")
>>> comp.get("name")
'api-layout'

>>> fold = gal_fold(kind="parameters", summary="Parameters (5)")
>>> fold.get("summary")
'Parameters (5)'
"""

from __future__ import annotations

from docutils import nodes


class gal_region(nodes.General, nodes.Element):
    """Legacy wrapper for a contiguous ``desc_content`` run.

    Parameters
    ----------
    kind : str
        One of ``"narrative"``, ``"fields"``, or ``"members"``.

    Examples
    --------
    >>> r = gal_region(kind="narrative")
    >>> isinstance(r, gal_region)
    True
    >>> r.get("kind")
    'narrative'
    """


class gal_fold(nodes.General, nodes.Element):
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
    >>> f = gal_fold(kind="parameters", summary="Parameters (3)")
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


class gal_sig_fold(nodes.General, nodes.Element):
    """Inline signature disclosure toggle for large parameter lists.

    The preview button lives in the signature row, while the full
    parameter list is rendered in a sibling ``api-signature-panel``
    wrapper beneath it.

    Parameters
    ----------
    first_param : str
        Text of the first parameter shown in collapsed preview.
    param_count : int
        Total number of parameters.
    panel_id : str
        DOM id of the controlled signature panel.

    Examples
    --------
    >>> sf = gal_sig_fold(first_param="host", param_count=13, panel_id="sig-panel")
    >>> sf.get("first_param")
    'host'
    >>> sf.get("param_count")
    13
    >>> sf.get("panel_id")
    'sig-panel'
    """
