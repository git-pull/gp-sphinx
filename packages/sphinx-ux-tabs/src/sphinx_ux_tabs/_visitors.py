"""HTML5 visitors for sphinx_ux_tabs nodes.

The HTML output is a single radio-input container per tab set:

.. code-block:: html

   <div class="gp-sphinx-tabs">
     <input type="radio" id="..-input-0" name="..-set-0" class="..__input" checked>
     <label for="..-input-0" class="..__label">First</label>
     <div class="..__panel">..</div>
     <input type="radio" id="..-input-1" name="..-set-0" class="..__input">
     <label for="..-input-1" class="..__label">Second</label>
     <div class="..__panel">..</div>
   </div>

The bundled CSS uses the ``:checked + label + .__panel`` adjacency
selector to show the active panel and style the active label.  No JS
is required for the basic switching behavior.

Examples
--------
>>> callable(visit_tab_set_html)
True

>>> callable(visit_tab_input_html)
True
"""

from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from sphinx.writers.html5 import HTML5Translator

    from sphinx_ux_tabs._nodes import (
        TabInputNode,
        TabItemNode,
        TabLabelNode,
        TabSetNode,
    )


def visit_tab_set_html(self: HTML5Translator, node: TabSetNode) -> None:
    """Open the outer ``<div class="gp-sphinx-tabs">``.

    Uses :meth:`starttag`, which auto-emits ``class="..."`` from
    ``node["classes"]``.

    Examples
    --------
    >>> visit_tab_set_html.__name__
    'visit_tab_set_html'
    """
    self.body.append(self.starttag(node, "div"))


def depart_tab_set_html(self: HTML5Translator, node: TabSetNode) -> None:
    """Close the outer tab-set ``</div>``.

    Examples
    --------
    >>> depart_tab_set_html.__name__
    'depart_tab_set_html'
    """
    del node
    self.body.append("</div>")


def visit_tab_item_html(self: HTML5Translator, node: TabItemNode) -> None:
    """Open a fallback ``<div>`` around the children.

    Reached only if a :class:`TabItemNode` survives the post-transform
    (a bug in :class:`TabsPostTransform`), but graceful so the build
    doesn't crash.  In normal flow every :class:`TabItemNode` is
    replaced by an ``[input, label, panel]`` triple before HTML
    rendering, so this fallback emits nothing visible by itself.

    Examples
    --------
    >>> visit_tab_item_html.__name__
    'visit_tab_item_html'
    """
    del node
    self.body.append('<div class="gp-sphinx-tabs__item">')


def depart_tab_item_html(self: HTML5Translator, node: TabItemNode) -> None:
    """Close the fallback ``</div>`` opened in :func:`visit_tab_item_html`."""
    del node
    self.body.append("</div>")


def visit_tab_input_html(self: HTML5Translator, node: TabInputNode) -> None:
    """Emit ``<input type="radio">`` — void element, no closing tag.

    Examples
    --------
    >>> visit_tab_input_html.__name__
    'visit_tab_input_html'
    """
    attrs: dict[str, t.Any] = {
        "type": "radio",
        "ids": [node["input_id"]],
        "name": node["set_name"],
    }
    if node["checked"]:
        attrs["checked"] = "checked"
    # ``emptytag`` would be ideal but ``self.starttag`` is well-tested for
    # the same shape; the lack of a depart-side write keeps it void.
    self.body.append(self.starttag(node, "input", "", **attrs))


def depart_tab_input_html(self: HTML5Translator, node: TabInputNode) -> None:
    """Do nothing — ``<input>`` is a void HTML element.

    Examples
    --------
    >>> depart_tab_input_html.__name__
    'depart_tab_input_html'
    """
    del node


def visit_tab_label_html(self: HTML5Translator, node: TabLabelNode) -> None:
    """Open ``<label for="...">`` and emit the data-sync attributes.

    Examples
    --------
    >>> visit_tab_label_html.__name__
    'visit_tab_label_html'
    """
    attrs: dict[str, t.Any] = {"for": node["input_id"]}
    sync_id = node.get("sync_id", "")
    if sync_id:
        attrs["data-sync-id"] = sync_id
        sync_group = node.get("sync_group", "tab")
        attrs["data-sync-group"] = sync_group
    self.body.append(self.starttag(node, "label", "", **attrs))


def depart_tab_label_html(self: HTML5Translator, node: TabLabelNode) -> None:
    """Close ``</label>``.

    Examples
    --------
    >>> depart_tab_label_html.__name__
    'depart_tab_label_html'
    """
    del node
    self.body.append("</label>")


__all__ = [
    "depart_tab_input_html",
    "depart_tab_item_html",
    "depart_tab_label_html",
    "depart_tab_set_html",
    "visit_tab_input_html",
    "visit_tab_item_html",
    "visit_tab_label_html",
    "visit_tab_set_html",
]
