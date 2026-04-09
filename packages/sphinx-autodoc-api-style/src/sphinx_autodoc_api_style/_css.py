"""CSS class name constants for sphinx_autodoc_api_style.

Re-exports ``SAB`` constants that replaced the old ``gas-*`` prefix.
Retained for backward compatibility; prefer importing from
``sphinx_autodoc_badges`` directly.

Examples
--------
>>> _CSS.BADGE_GROUP
'sab-badge-group'

>>> _CSS.BADGE
'sab-badge'

>>> _CSS.obj_type("function")
'sab-type-function'

>>> _CSS.TOOLBAR
'sab-toolbar'
"""

from __future__ import annotations

from sphinx_autodoc_badges import SAB


class _CSS:
    """CSS class name constants (re-exports from SAB).

    Examples
    --------
    >>> _CSS.PREFIX
    'sab'

    >>> _CSS.BADGE_GROUP
    'sab-badge-group'

    >>> _CSS.TOOLBAR
    'sab-toolbar'

    >>> _CSS.obj_type("class")
    'sab-type-class'
    """

    PREFIX = SAB.PREFIX
    BADGE_GROUP = SAB.BADGE_GROUP
    BADGE = SAB.BADGE

    BADGE_TYPE = SAB.BADGE_TYPE
    BADGE_MOD = SAB.BADGE_MOD

    MOD_ASYNC = SAB.MOD_ASYNC
    MOD_CLASSMETHOD = SAB.MOD_CLASSMETHOD
    MOD_STATICMETHOD = SAB.MOD_STATICMETHOD
    MOD_ABSTRACT = SAB.MOD_ABSTRACT
    MOD_FINAL = SAB.MOD_FINAL
    DEPRECATED = SAB.STATE_DEPRECATED

    TOOLBAR = SAB.TOOLBAR

    @staticmethod
    def obj_type(name: str) -> str:
        """Return the type-specific CSS class, e.g. ``sab-type-function``.

        Parameters
        ----------
        name : str
            Python domain object type name.

        Returns
        -------
        str
            CSS class string.

        Examples
        --------
        >>> _CSS.obj_type("method")
        'sab-type-method'

        >>> _CSS.obj_type("exception")
        'sab-type-exception'
        """
        return SAB.obj_type(name)
