"""Shared CSS class name constants for sphinx_autodoc_badges.

Examples
--------
>>> SAB.BADGE
'sab-badge'

>>> SAB.BADGE_GROUP
'sab-badge-group'

>>> SAB.TOOLBAR
'sab-toolbar'

>>> SAB.ICON_ONLY
'sab-icon-only'
"""

from __future__ import annotations


class SAB:
    """CSS class constants (``sab-`` = sphinx autodoc badges).

    Examples
    --------
    >>> SAB.PREFIX
    'sab'

    >>> SAB.OUTLINE
    'sab-outline'
    """

    PREFIX = "sab"
    BADGE = f"{PREFIX}-badge"
    BADGE_GROUP = f"{PREFIX}-badge-group"
    TOOLBAR = f"{PREFIX}-toolbar"
    ICON_ONLY = f"{PREFIX}-icon-only"
    INLINE_ICON = f"{PREFIX}-inline-icon"
    OUTLINE = f"{PREFIX}-outline"
    FILLED = f"{PREFIX}-filled"
