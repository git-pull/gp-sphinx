"""CSS class name constants for sphinx_autodoc_fastmcp.

All constants use the ``gp-sphinx-fastmcp`` namespace for FastMCP-specific
layout and toolset semantics.  For shared badge primitives, import ``SAB``
from ``sphinx_ux_badges`` directly.

Examples
--------
>>> _CSS.TOOL_SECTION
'gp-sphinx-fastmcp__tool-section'

>>> _CSS.BADGE_TOOLSET
'gp-sphinx-fastmcp__toolset'
"""

from __future__ import annotations


class _CSS:
    """CSS class name constants (``gp-sphinx-fastmcp`` namespace)."""

    PREFIX = "gp-sphinx-fastmcp"

    # Layout
    TOOL_SECTION = "gp-sphinx-fastmcp__tool-section"
    SECTION_TITLE_HIDDEN = "gp-sphinx-fastmcp__visually-hidden"
    TYPE_TOOL = "gp-sphinx-fastmcp__type-tool"
    TYPE_PROMPT = "gp-sphinx-fastmcp__type-prompt"
    TYPE_RESOURCE = "gp-sphinx-fastmcp__type-resource"
    TYPE_RESOURCE_TEMPLATE = "gp-sphinx-fastmcp__type-resource-template"
    BADGE_MIME = "gp-sphinx-fastmcp__mime"
    BADGE_TAG = "gp-sphinx-fastmcp__tag"
    TOOL_ENTRY = "gp-sphinx-fastmcp__tool-entry"
    TOOL_SIGNATURE = "gp-sphinx-fastmcp__tool-signature"
    PROMPT_SECTION = "gp-sphinx-fastmcp__prompt-section"
    PROMPT_ENTRY = "gp-sphinx-fastmcp__prompt-entry"
    PROMPT_SIGNATURE = "gp-sphinx-fastmcp__prompt-signature"
    RESOURCE_SECTION = "gp-sphinx-fastmcp__resource-section"
    RESOURCE_ENTRY = "gp-sphinx-fastmcp__resource-entry"
    RESOURCE_SIGNATURE = "gp-sphinx-fastmcp__resource-signature"
    BODY_SECTION = "gp-sphinx-fastmcp__body-section"

    # Toolset slot + values
    BADGE_TOOLSET = "gp-sphinx-fastmcp__toolset"
    TOOLSET_INSPECT = "gp-sphinx-fastmcp__toolset-readonly"
    TOOLSET_MANAGE = "gp-sphinx-fastmcp__toolset-mutating"
    TOOLSET_TEARDOWN = "gp-sphinx-fastmcp__toolset-destructive"

    @staticmethod
    def tone_class(tone: str) -> str:
        """Return the badge colour class for a toolset's tone.

        Examples
        --------
        >>> _CSS.tone_class("red")
        'gp-sphinx-fastmcp__toolset--tone-red'
        """
        return f"gp-sphinx-fastmcp__toolset--tone-{tone}"

    @staticmethod
    def toolset_class(toolset: str) -> str:
        """Return toolset modifier class for badge styling.

        Examples
        --------
        >>> _CSS.toolset_class("readonly")
        'gp-sphinx-fastmcp__toolset-readonly'
        """
        return f"gp-sphinx-fastmcp__toolset-{toolset}"
