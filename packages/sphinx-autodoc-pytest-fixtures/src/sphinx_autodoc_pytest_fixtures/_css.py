from __future__ import annotations

from sphinx_autodoc_badges import SAB


class _CSS:
    """CSS class name constants for sphinx_autodoc_pytest_fixtures.

    Re-exports SAB constants that replaced the old ``spf-*`` prefix.
    Retained for backward compatibility; prefer using ``SAB`` directly.
    """

    PREFIX = SAB.PREFIX
    BADGE_GROUP = SAB.BADGE_GROUP
    BADGE = SAB.BADGE
    BADGE_SCOPE = SAB.BADGE_SCOPE
    BADGE_KIND = SAB.BADGE_KIND
    BADGE_STATE = SAB.BADGE_STATE
    BADGE_FIXTURE = SAB.BADGE_FIXTURE
    FACTORY = SAB.STATE_FACTORY
    OVERRIDE = SAB.STATE_OVERRIDE
    AUTOUSE = SAB.STATE_AUTOUSE
    DEPRECATED = SAB.STATE_DEPRECATED
    # Layout-only (not badges)
    FIXTURE_INDEX = "spf-fixture-index"
    TABLE_SCROLL = "spf-table-scroll"

    @staticmethod
    def scope(name: str) -> str:
        """Return the scope-specific CSS class, e.g. ``sab-scope-session``.

        Examples
        --------
        >>> _CSS.scope("session")
        'sab-scope-session'
        """
        return SAB.scope(name)
