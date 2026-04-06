"""CSS class name constants for sphinx_autodoc_api_style.

Centralises every ``gas-*`` class name so the extension and stylesheet
stay in sync.  Tests import this class to assert on rendered output.

Examples
--------
>>> _CSS.BADGE_GROUP
'gas-badge-group'

>>> _CSS.BADGE
'gas-badge'

>>> _CSS.obj_type("function")
'gas-type-function'
"""

from __future__ import annotations


class _CSS:
    """CSS class name constants for API style badges.

    All class names use the ``gas-`` prefix (gp-sphinx api style) to avoid
    collision with ``spf-`` (sphinx pytest fixtures) or other extensions.

    Examples
    --------
    >>> _CSS.PREFIX
    'gas'

    >>> _CSS.BADGE_GROUP
    'gas-badge-group'

    >>> _CSS.TOOLBAR
    'gas-toolbar'

    >>> _CSS.obj_type("class")
    'gas-type-class'
    """

    PREFIX = "gas"
    BADGE_GROUP = f"{PREFIX}-badge-group"
    BADGE = f"{PREFIX}-badge"

    BADGE_TYPE = f"{PREFIX}-badge--type"
    BADGE_MOD = f"{PREFIX}-badge--mod"

    MOD_ASYNC = f"{PREFIX}-mod-async"
    MOD_CLASSMETHOD = f"{PREFIX}-mod-classmethod"
    MOD_STATICMETHOD = f"{PREFIX}-mod-staticmethod"
    MOD_ABSTRACT = f"{PREFIX}-mod-abstract"
    MOD_FINAL = f"{PREFIX}-mod-final"
    DEPRECATED = f"{PREFIX}-deprecated"

    TOOLBAR = f"{PREFIX}-toolbar"

    @staticmethod
    def obj_type(name: str) -> str:
        """Return the type-specific CSS class, e.g. ``gas-type-function``.

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
        'gas-type-method'

        >>> _CSS.obj_type("exception")
        'gas-type-exception'
        """
        return f"{_CSS.PREFIX}-type-{name}"
