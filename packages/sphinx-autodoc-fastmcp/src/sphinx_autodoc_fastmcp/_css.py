"""CSS class name constants for sphinx_autodoc_fastmcp.

Examples
--------
>>> _CSS.PREFIX
'smf'

>>> _CSS.BADGE_GROUP
'smf-badge-group'

>>> _CSS.TOOLBAR
'smf-toolbar'

>>> _CSS.TOOL_SECTION
'smf-tool-section'
"""

from __future__ import annotations


class _CSS:
    """CSS class name constants (``smf-`` = sphinx autodoc fastmcp)."""

    PREFIX = "smf"
    TOOL_SECTION = f"{PREFIX}-tool-section"
    BADGE_GROUP = f"{PREFIX}-badge-group"
    BADGE = f"{PREFIX}-badge"
    BADGE_TYPE = f"{PREFIX}-badge--type"
    BADGE_SAFETY = f"{PREFIX}-badge--safety"
    TOOLBAR = f"{PREFIX}-toolbar"
    SECTION_TITLE_HIDDEN = f"{PREFIX}-visually-hidden"
    TYPE_TOOL = f"{PREFIX}-type-tool"

    SAFETY_READONLY = f"{PREFIX}-safety-readonly"
    SAFETY_MUTATING = f"{PREFIX}-safety-mutating"
    SAFETY_DESTRUCTIVE = f"{PREFIX}-safety-destructive"

    @staticmethod
    def safety_class(safety: str) -> str:
        """Return safety modifier class for badge styling."""
        return f"{_CSS.PREFIX}-safety-{safety}"
