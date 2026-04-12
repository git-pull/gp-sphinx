"""Componentized layout for Sphinx object-description output.

Preserves Sphinx's outer ``dl / dt / dd`` structure while rebuilding
managed Sphinx object entries into stable ``api-*`` components.

Examples
--------
>>> from sphinx_ux_autodoc_layout import setup
>>> callable(setup)
True
"""

from __future__ import annotations

import pathlib
import typing as t

from sphinx import addnodes

from sphinx_ux_autodoc_layout._cards import build_api_card_entry
from sphinx_ux_autodoc_layout._nodes import (
    api_component,
    api_fold,
    api_inline_component,
    api_permalink,
    api_region,
    api_sig_fold,
    api_slot,
    build_api_component,
    build_api_inline_component,
    build_api_slot,
)
from sphinx_ux_autodoc_layout._render import iter_desc_nodes, parse_generated_markup
from sphinx_ux_autodoc_layout._sections import (
    ApiFactRow,
    build_api_facts_section,
    build_api_section,
    build_api_summary_section,
    build_api_table_section,
)
from sphinx_ux_autodoc_layout._slots import inject_signature_slots, is_viewcode_ref
from sphinx_ux_autodoc_layout._transforms import on_doctree_resolved
from sphinx_ux_autodoc_layout._visitors import (
    depart_api_component,
    depart_api_fold,
    depart_api_permalink,
    depart_api_region,
    depart_api_sig_fold,
    depart_desc_signature_html,
    passthrough_depart,
    passthrough_visit,
    visit_api_component,
    visit_api_fold,
    visit_api_permalink,
    visit_api_region,
    visit_api_sig_fold,
    visit_desc_signature_html,
)

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = [
    "ApiFactRow",
    "api_component",
    "api_fold",
    "api_inline_component",
    "api_permalink",
    "api_region",
    "api_sig_fold",
    "api_slot",
    "build_api_card_entry",
    "build_api_component",
    "build_api_facts_section",
    "build_api_inline_component",
    "build_api_section",
    "build_api_slot",
    "build_api_summary_section",
    "build_api_table_section",
    "inject_signature_slots",
    "is_viewcode_ref",
    "iter_desc_nodes",
    "on_doctree_resolved",
    "parse_generated_markup",
    "setup",
]


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register the extension with Sphinx.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application object.

    Returns
    -------
    dict[str, Any]
        Extension metadata.

    Examples
    --------
    >>> setup  # doctest: +ELLIPSIS
    <function setup at 0x...>
    """
    # Config values
    app.add_config_value(
        "api_layout_enabled", default=False, rebuild="env", types=(bool,)
    )
    app.add_config_value(
        "api_fold_parameters", default=True, rebuild="env", types=(bool,)
    )
    app.add_config_value(
        "api_collapsed_threshold", default=10, rebuild="env", types=(int,)
    )
    app.add_config_value(
        "api_signature_show_annotations", default=True, rebuild="env", types=(bool,)
    )

    # Custom nodes with HTML visitors + passthrough for other builders
    _pt = (passthrough_visit, passthrough_depart)
    app.add_node(
        api_region,
        html=(visit_api_region, depart_api_region),
        latex=_pt,
        text=_pt,
        man=_pt,
        texinfo=_pt,
    )
    app.add_node(
        api_fold,
        html=(visit_api_fold, depart_api_fold),
        latex=_pt,
        text=_pt,
        man=_pt,
        texinfo=_pt,
    )
    app.add_node(
        api_sig_fold,
        html=(visit_api_sig_fold, depart_api_sig_fold),
        latex=_pt,
        text=_pt,
        man=_pt,
        texinfo=_pt,
    )
    app.add_node(
        api_component,
        html=(visit_api_component, depart_api_component),
        latex=_pt,
        text=_pt,
        man=_pt,
        texinfo=_pt,
    )
    app.add_node(
        api_inline_component,
        html=(visit_api_component, depart_api_component),
        latex=_pt,
        text=_pt,
        man=_pt,
        texinfo=_pt,
    )
    app.add_node(
        api_slot,
        html=_pt,
        latex=_pt,
        text=_pt,
        man=_pt,
        texinfo=_pt,
    )
    app.add_node(
        api_permalink,
        html=(visit_api_permalink, depart_api_permalink),
        latex=_pt,
        text=_pt,
        man=_pt,
        texinfo=_pt,
    )

    # Managed desc signatures keep Sphinx's outer ``dt`` handling but skip the
    # stock permalink injection so layout can place ``api-link`` explicitly.
    app.add_node(
        addnodes.desc_signature,
        override=True,
        html=(visit_desc_signature_html, depart_desc_signature_html),
    )

    # Transform: doctree-resolved at priority 600 (after api-style at 500)
    app.connect("doctree-resolved", on_doctree_resolved, priority=600)

    # Static assets
    _static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if _static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(_static_dir)

    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/layout.css")
    app.add_js_file("js/layout.js", loading_method="defer")

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
