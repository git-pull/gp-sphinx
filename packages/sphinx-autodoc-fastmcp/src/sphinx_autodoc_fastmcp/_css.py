"""CSS class name constants for sphinx_autodoc_fastmcp.

All constants use the ``smf-`` prefix for FastMCP-specific layout
and safety semantics.  For shared badge primitives, import ``SAB``
from ``sphinx_autodoc_badges`` directly.

Examples
--------
>>> _CSS.TOOL_SECTION
'smf-tool-section'

>>> _CSS.BADGE_SAFETY
'smf-badge--safety'
"""

from __future__ import annotations


class _CSS:
    """CSS class name constants (``smf-`` = sphinx autodoc fastmcp)."""

    PREFIX = "smf"

    # Layout
    TOOL_SECTION = f"{PREFIX}-tool-section"
    SECTION_TITLE_HIDDEN = f"{PREFIX}-visually-hidden"
    TYPE_TOOL = f"{PREFIX}-type-tool"
    TOOL_ENTRY = f"{PREFIX}-tool-entry"
    TOOL_SIGNATURE = f"{PREFIX}-tool-signature"
    BODY_SECTION = f"{PREFIX}-body-section"

    # Safety tiers
    BADGE_SAFETY = f"{PREFIX}-badge--safety"
    SAFETY_READONLY = f"{PREFIX}-safety-readonly"
    SAFETY_MUTATING = f"{PREFIX}-safety-mutating"
    SAFETY_DESTRUCTIVE = f"{PREFIX}-safety-destructive"

    @staticmethod
    def safety_class(safety: str) -> str:
        """Return safety modifier class for badge styling.

        Examples
        --------
        >>> _CSS.safety_class("readonly")
        'smf-safety-readonly'
        """
        return f"{_CSS.PREFIX}-safety-{safety}"
