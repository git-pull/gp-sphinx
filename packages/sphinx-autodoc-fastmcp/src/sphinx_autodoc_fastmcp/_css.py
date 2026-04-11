"""CSS class name constants for sphinx_autodoc_fastmcp.

Re-exports shared ``SAB`` constants for badge primitives.
Retains ``smf-`` prefix for FastMCP-specific layout and safety classes.

Examples
--------
>>> _CSS.BADGE_GROUP
'sab-badge-group'

>>> _CSS.TOOLBAR
'sab-toolbar'

>>> _CSS.TOOL_SECTION
'smf-tool-section'

>>> _CSS.BADGE_SAFETY
'smf-badge--safety'
"""

from __future__ import annotations

from sphinx_autodoc_badges import SAB


class _CSS:
    """CSS class name constants (shared ``sab-`` + local ``smf-``)."""

    PREFIX = "smf"

    # Shared badge primitives (re-exported from SAB)
    BADGE_GROUP = SAB.BADGE_GROUP
    BADGE = SAB.BADGE
    BADGE_TYPE = SAB.BADGE_TYPE
    TOOLBAR = SAB.TOOLBAR

    # FastMCP-specific layout
    TOOL_SECTION = f"{PREFIX}-tool-section"
    SECTION_TITLE_HIDDEN = f"{PREFIX}-visually-hidden"
    TYPE_TOOL = f"{PREFIX}-type-tool"
    TOOL_ENTRY = f"{PREFIX}-tool-entry"
    TOOL_SIGNATURE = f"{PREFIX}-tool-signature"
    BODY_SECTION = f"{PREFIX}-body-section"

    # FastMCP-specific safety tiers
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
