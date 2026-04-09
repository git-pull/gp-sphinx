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

>>> SAB.XXS
'sab-xxs'

>>> SAB.MD
'sab-md'

>>> SAB.SM
'sab-sm'

>>> SAB.TYPE_FUNCTION
'sab-type-function'

>>> SAB.TYPE_FIXTURE
'sab-type-fixture'

>>> SAB.SCOPE_SESSION
'sab-scope-session'

>>> SAB.TYPE_CONFIG
'sab-type-config'
"""

from __future__ import annotations


class SAB:
    """CSS class constants (``sab-`` = sphinx autodoc badges).

    Covers both structural variants (size, outline, icon-only) and the
    unified semantic colour palette from ``sab_palettes.css``.  Every
    ``sphinx-autodoc-*`` package uses these constants instead of defining
    its own ``gas-*`` / ``spf-*`` / ``sas-*`` / ``sadoc-*`` strings.

    Examples
    --------
    >>> SAB.PREFIX
    'sab'

    >>> SAB.OUTLINE
    'sab-outline'

    >>> SAB.TYPE_METHOD
    'sab-type-method'

    >>> SAB.STATE_AUTOUSE
    'sab-state-autouse'
    """

    PREFIX = "sab"

    # ── Structural / layout ──────────────────────────────
    BADGE = f"{PREFIX}-badge"
    BADGE_GROUP = f"{PREFIX}-badge-group"
    TOOLBAR = f"{PREFIX}-toolbar"
    ICON_ONLY = f"{PREFIX}-icon-only"
    INLINE_ICON = f"{PREFIX}-inline-icon"
    OUTLINE = f"{PREFIX}-outline"
    FILLED = f"{PREFIX}-filled"
    ICON_RIGHT = f"{PREFIX}-icon-right"

    # Underline control (compose with sab-dense or any badge)
    NO_UNDERLINE = f"{PREFIX}-no-underline"
    UNDERLINE = f"{PREFIX}-underline"
    UNDERLINE_DOTTED = f"{PREFIX}-underline-dotted"
    UNDERLINE_SOLID = f"{PREFIX}-underline-solid"

    # Size variants
    XXS = f"{PREFIX}-xxs"
    XS = f"{PREFIX}-xs"
    SM = f"{PREFIX}-sm"
    MD = f"{PREFIX}-md"
    LG = f"{PREFIX}-lg"
    XL = f"{PREFIX}-xl"

    # Dense variant (compact, always-bordered, dotted-underline)
    DENSE = f"{PREFIX}-dense"

    # ── Python API type badges (filled) ──────────────────
    TYPE_FUNCTION = f"{PREFIX}-type-function"
    TYPE_CLASS = f"{PREFIX}-type-class"
    TYPE_METHOD = f"{PREFIX}-type-method"
    TYPE_PROPERTY = f"{PREFIX}-type-property"
    TYPE_ATTRIBUTE = f"{PREFIX}-type-attribute"
    TYPE_DATA = f"{PREFIX}-type-data"
    TYPE_EXCEPTION = f"{PREFIX}-type-exception"
    TYPE_TYPEALIAS = f"{PREFIX}-type-typealias"
    TYPE_MODULE = f"{PREFIX}-type-module"

    # Slot markers (filled / outlined) for Python API badges
    BADGE_TYPE = f"{PREFIX}-badge--type"
    BADGE_MOD = f"{PREFIX}-badge--mod"

    # ── Python API modifier badges (outlined) ────────────
    MOD_ASYNC = f"{PREFIX}-mod-async"
    MOD_CLASSMETHOD = f"{PREFIX}-mod-classmethod"
    MOD_STATICMETHOD = f"{PREFIX}-mod-staticmethod"
    MOD_ABSTRACT = f"{PREFIX}-mod-abstract"
    MOD_FINAL = f"{PREFIX}-mod-final"

    # Sphinx config rebuild-mode badge (outlined)
    MOD_REBUILD = f"{PREFIX}-mod-rebuild"

    # ── Shared deprecated state ───────────────────────────
    STATE_DEPRECATED = f"{PREFIX}-state-deprecated"

    # ── pytest fixture type (filled green) ───────────────
    TYPE_FIXTURE = f"{PREFIX}-type-fixture"

    # Slot markers for fixture badges
    BADGE_FIXTURE = f"{PREFIX}-badge--fixture"
    BADGE_SCOPE = f"{PREFIX}-badge--scope"
    BADGE_KIND = f"{PREFIX}-badge--kind"
    BADGE_STATE = f"{PREFIX}-badge--state"

    # ── pytest fixture scopes (filled) ───────────────────
    SCOPE_SESSION = f"{PREFIX}-scope-session"
    SCOPE_MODULE = f"{PREFIX}-scope-module"
    SCOPE_CLASS = f"{PREFIX}-scope-class"

    # ── pytest fixture kinds / states (outlined) ─────────
    STATE_FACTORY = f"{PREFIX}-state-factory"
    STATE_OVERRIDE = f"{PREFIX}-state-override"
    STATE_AUTOUSE = f"{PREFIX}-state-autouse"

    # ── Sphinx config (filled amber) ─────────────────────
    TYPE_CONFIG = f"{PREFIX}-type-config"

    # ── docutils (filled violet) ─────────────────────────
    TYPE_DIRECTIVE = f"{PREFIX}-type-directive"
    TYPE_ROLE = f"{PREFIX}-type-role"
    TYPE_OPTION = f"{PREFIX}-type-option"

    @staticmethod
    def obj_type(name: str) -> str:
        """Return the type-specific CSS class for a Python API object.

        Parameters
        ----------
        name : str
            Python domain object type name.

        Returns
        -------
        str
            CSS class string, e.g. ``"sab-type-function"``.

        Examples
        --------
        >>> SAB.obj_type("method")
        'sab-type-method'

        >>> SAB.obj_type("exception")
        'sab-type-exception'
        """
        return f"{SAB.PREFIX}-type-{name}"

    @staticmethod
    def scope(name: str) -> str:
        """Return the scope-specific CSS class for a pytest fixture.

        Parameters
        ----------
        name : str
            Fixture scope string (``"session"``, ``"module"``, ``"class"``).

        Returns
        -------
        str
            CSS class string, e.g. ``"sab-scope-session"``.

        Examples
        --------
        >>> SAB.scope("session")
        'sab-scope-session'

        >>> SAB.scope("module")
        'sab-scope-module'
        """
        return f"{SAB.PREFIX}-scope-{name}"
