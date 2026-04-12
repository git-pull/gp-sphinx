"""Sphinx extension for documenting FastMCP tools (cards, badges, cross-refs).

Examples
--------
>>> from sphinx_autodoc_fastmcp import setup
>>> callable(setup)
True
"""

from __future__ import annotations

import logging
import pathlib
import typing as t

from sphinx.application import Sphinx

from sphinx_autodoc_fastmcp._collector import collect_tools
from sphinx_autodoc_fastmcp._directives import (
    FastMCPToolDirective,
    FastMCPToolInputDirective,
    FastMCPToolSummaryDirective,
)
from sphinx_autodoc_fastmcp._roles import (
    _tool_role,
    _toolicon_role,
    _tooliconil_role,
    _tooliconir_role,
    _tooliconl_role,
    _tooliconr_role,
    _toolref_role,
)
from sphinx_autodoc_fastmcp._transforms import (
    add_section_badges,
    badge_role,
    collect_tool_section_content,
    register_tool_labels,
    resolve_tool_refs,
)

__all__ = [
    "setup",
]

logging.getLogger(__name__).addHandler(logging.NullHandler())

_EXTENSION_VERSION = "0.0.1a8"


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register the ``sphinx_autodoc_fastmcp`` extension.

    Parameters
    ----------
    app : Sphinx
        Sphinx application.

    Returns
    -------
    dict[str, Any]
        Extension metadata (version, parallel flags).

    Examples
    --------
    >>> from sphinx_autodoc_fastmcp import setup
    >>> callable(setup)
    True
    """
    app.setup_extension("sphinx_ux_badges")
    app.setup_extension("sphinx_ux_autodoc_layout")
    app.setup_extension("sphinx_autodoc_typehints_gp")

    app.add_config_value("fastmcp_tool_modules", [], "env")
    app.add_config_value("fastmcp_area_map", {}, "env")
    app.add_config_value("fastmcp_model_module", "", "env")
    app.add_config_value("fastmcp_model_classes", (), "env")
    app.add_config_value("fastmcp_section_badge_map", {}, "env")
    app.add_config_value("fastmcp_section_badge_pages", (), "env")
    app.add_config_value("fastmcp_collector_mode", "register", "env")

    _static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if _static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(_static_dir)

    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/sphinx_autodoc_fastmcp.css")

    app.connect("builder-inited", collect_tools)
    app.connect("doctree-read", register_tool_labels)
    app.connect("doctree-read", collect_tool_section_content)
    app.connect("doctree-resolved", add_section_badges)
    app.connect("doctree-resolved", resolve_tool_refs)

    app.add_role("tool", _tool_role)
    app.add_role("toolref", _toolref_role)
    app.add_role("toolicon", _toolicon_role)
    app.add_role("tooliconl", _tooliconl_role)
    app.add_role("tooliconr", _tooliconr_role)
    app.add_role("tooliconil", _tooliconil_role)
    app.add_role("tooliconir", _tooliconir_role)
    app.add_role("badge", badge_role)

    app.add_directive("fastmcp-tool", FastMCPToolDirective)
    app.add_directive("fastmcp-tool-input", FastMCPToolInputDirective)
    app.add_directive("fastmcp-tool-summary", FastMCPToolSummaryDirective)

    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
