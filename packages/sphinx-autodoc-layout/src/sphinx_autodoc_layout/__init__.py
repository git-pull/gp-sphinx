"""Componentized layout for Sphinx autodoc output.

Wraps contiguous ``desc_content`` runs into semantic ``gal_region``
nodes and folds large parameter sections with ``gal_fold`` disclosure
blocks.  Does not modify ``desc_signature`` -- that is owned by Sphinx
and ``sphinx-autodoc-api-style``.

Examples
--------
>>> from sphinx_autodoc_layout import setup
>>> callable(setup)
True
"""

from __future__ import annotations

import pathlib
import typing as t

from sphinx_autodoc_layout._nodes import gal_fold, gal_region
from sphinx_autodoc_layout._transforms import on_doctree_resolved
from sphinx_autodoc_layout._visitors import (
    depart_gal_fold,
    depart_gal_region,
    passthrough_depart,
    passthrough_visit,
    visit_gal_fold,
    visit_gal_region,
)

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx


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
    app.add_config_value("gal_enabled", default=False, rebuild="env", types=(bool,))
    app.add_config_value(
        "gal_fold_parameters", default=True, rebuild="env", types=(bool,)
    )
    app.add_config_value(
        "gal_collapsed_threshold", default=10, rebuild="env", types=(int,)
    )

    # Custom nodes with HTML visitors + passthrough for other builders
    _pt = (passthrough_visit, passthrough_depart)
    app.add_node(
        gal_region,
        html=(visit_gal_region, depart_gal_region),
        latex=_pt,
        text=_pt,
        man=_pt,
        texinfo=_pt,
    )
    app.add_node(
        gal_fold,
        html=(visit_gal_fold, depart_gal_fold),
        latex=_pt,
        text=_pt,
        man=_pt,
        texinfo=_pt,
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
