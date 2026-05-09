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

from sphinx_autodoc_fastmcp._collector import (
    collect_prompts_and_resources,
    collect_tools,
)
from sphinx_autodoc_fastmcp._directives import (
    FastMCPPromptDirective,
    FastMCPPromptInputDirective,
    FastMCPResourceDirective,
    FastMCPResourceTemplateDirective,
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

_EXTENSION_VERSION = "0.0.1a17"


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

    app.add_config_value(
        "fastmcp_tool_modules",
        [],
        "env",
        description=(
            "Dotted module paths whose ``register(server)`` hooks expose "
            "FastMCP tools to autodoc. Each module is imported once at "
            "``builder-inited`` and its tools are added to the rendered "
            "reference."
        ),
    )
    app.add_config_value(
        "fastmcp_area_map",
        {},
        "env",
        description=(
            'Mapping of tool-module suffix (e.g. ``"session_tools"``) '
            "to the docs area page that owns its tools (e.g. "
            '``"sessions"``). Drives cross-reference resolution and '
            "the area badge in card layouts."
        ),
    )
    app.add_config_value(
        "fastmcp_model_module",
        "",
        "env",
        description=(
            "Dotted module containing the Pydantic model classes "
            "referenced by tool return types. Used to resolve "
            "``{fastmcp-model}`` cross-references."
        ),
    )
    app.add_config_value(
        "fastmcp_model_classes",
        (),
        "env",
        description=(
            "Iterable of model class names within ``fastmcp_model_module`` "
            "to autodoc. Empty default skips model rendering entirely."
        ),
    )
    app.add_config_value(
        "fastmcp_section_badge_map",
        {},
        "env",
        description=(
            'Mapping of docstring section heading (e.g. ``"Inspect"``) '
            "to the safety badge it should render with (e.g. "
            '``"readonly"``, ``"mutating"``, ``"destructive"``). '
            "Drives the inline section pills next to grouped tool lists."
        ),
    )
    app.add_config_value(
        "fastmcp_section_badge_pages",
        (),
        "env",
        description=(
            "Iterable of docnames where ``fastmcp_section_badge_map`` "
            "should be applied. Pages outside this list render plain "
            "section headings."
        ),
    )
    app.add_config_value(
        "fastmcp_collector_mode",
        "register",
        "env",
        description=(
            "How tools are gathered from each ``fastmcp_tool_modules`` "
            'entry. ``"register"`` calls the module\'s ``register(server)`` '
            'hook (the FastMCP convention); ``"introspect"`` walks '
            "module attributes for ``@server.tool``-decorated callables."
        ),
    )
    app.add_config_value(
        "fastmcp_server_module",
        "",
        "env",
        description=(
            '``"pkg.module:attribute"`` path to a live ``FastMCP`` '
            "instance. When set, the prompt / resource collector reads "
            "``local_provider._components`` directly so docs enumerate "
            "the same surface as the running server."
        ),
    )

    _static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if _static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(_static_dir)

    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/sphinx_autodoc_fastmcp.css")

    app.connect("builder-inited", collect_tools)
    app.connect("builder-inited", collect_prompts_and_resources)
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
    app.add_directive("fastmcp-prompt", FastMCPPromptDirective)
    app.add_directive("fastmcp-prompt-input", FastMCPPromptInputDirective)
    app.add_directive("fastmcp-resource", FastMCPResourceDirective)
    app.add_directive("fastmcp-resource-template", FastMCPResourceTemplateDirective)

    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
