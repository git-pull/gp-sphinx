"""Drop-in tabs replacement for sphinx-inline-tabs and sphinx-design.

Provides three directives — ``.. tab::`` (sphinx-inline-tabs compatible
with ``:new-set:``), ``.. tab-set::`` and ``.. tab-item::``
(sphinx-design compatible) — backed by a two-pass post-transform that
groups consecutive ``.. tab::`` siblings and then expands every tab set
into a flat sequence of ``[input, label, panel]`` triples the bundled
CSS can switch with the ``:checked + label + .__panel`` adjacency
selector.  No runtime JavaScript is required for the basic switching
behavior; the bundled JS only powers cross-set ``:sync:``
synchronization and re-binds itself after every gp-sphinx SPA
navigation via the ``gp-sphinx:navigated`` event.

Examples
--------
>>> from sphinx_ux_tabs import SUT, setup
>>> SUT.TABS
'gp-sphinx-tabs'

>>> callable(setup)
True
"""

from __future__ import annotations

import logging
import pathlib
import typing as t

from sphinx.application import Sphinx

from sphinx_ux_tabs._css import SUT
from sphinx_ux_tabs._directives import (
    TabDirective,
    TabItemDirective,
    TabSetDirective,
)
from sphinx_ux_tabs._nodes import (
    TabContainer,
    TabInputNode,
    TabItemNode,
    TabLabelNode,
    TabSetNode,
)
from sphinx_ux_tabs._transforms import TabsPostTransform
from sphinx_ux_tabs._visitors import (
    depart_tab_input_html,
    depart_tab_item_html,
    depart_tab_label_html,
    depart_tab_set_html,
    visit_tab_input_html,
    visit_tab_item_html,
    visit_tab_label_html,
    visit_tab_set_html,
)

__all__ = [
    "SUT",
    "TabContainer",
    "TabDirective",
    "TabInputNode",
    "TabItemDirective",
    "TabItemNode",
    "TabLabelNode",
    "TabSetDirective",
    "TabSetNode",
    "TabsPostTransform",
    "setup",
]

logging.getLogger(__name__).addHandler(logging.NullHandler())

_EXTENSION_VERSION = "0.0.1a18"


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register the three tab directives, custom nodes, and bundled assets.

    Parameters
    ----------
    app : Sphinx
        Sphinx application.

    Returns
    -------
    dict[str, Any]
        Extension metadata.

    Examples
    --------
    >>> from sphinx_ux_tabs import setup
    >>> callable(setup)
    True
    """
    # Nodes that materialise in the final doctree need HTML visitors; the
    # transient containers (TabContainer, TabItemNode) fall back to the
    # default container visitor of their docutils base for non-HTML output.
    app.add_node(TabSetNode, html=(visit_tab_set_html, depart_tab_set_html))
    app.add_node(TabItemNode, html=(visit_tab_item_html, depart_tab_item_html))
    app.add_node(TabInputNode, html=(visit_tab_input_html, depart_tab_input_html))
    app.add_node(TabLabelNode, html=(visit_tab_label_html, depart_tab_label_html))

    app.add_directive("tab", TabDirective)
    app.add_directive("tab-set", TabSetDirective)
    app.add_directive("tab-item", TabItemDirective)
    app.add_post_transform(TabsPostTransform)

    _static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if _static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(_static_dir)

    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/sphinx_ux_tabs.css")
    app.add_js_file("js/sphinx_ux_tabs_sync.js")

    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
