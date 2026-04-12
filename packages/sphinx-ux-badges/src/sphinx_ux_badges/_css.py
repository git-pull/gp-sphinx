"""Shared CSS class name constants for sphinx_ux_badges.

Examples
--------
>>> SAB.BADGE
'gp-sphinx-badge'

>>> SAB.BADGE_GROUP
'gp-sphinx-badge-group'

>>> SAB.TOOLBAR
'gp-sphinx-toolbar'

>>> SAB.ICON_ONLY
'gp-sphinx-badge--icon-only'

>>> SAB.XXS
'gp-sphinx-badge--size-xxs'

>>> SAB.MD
'gp-sphinx-badge--size-md'

>>> SAB.SM
'gp-sphinx-badge--size-sm'

>>> SAB.TYPE_FUNCTION
'gp-sphinx-badge--type-function'

>>> SAB.TYPE_FIXTURE
'gp-sphinx-badge--type-fixture'

>>> SAB.SCOPE_SESSION
'gp-sphinx-badge--scope-session'

>>> SAB.TYPE_CONFIG
'gp-sphinx-badge--type-config'
"""

from __future__ import annotations


class SAB:
    """CSS class constants under the ``gp-sphinx-`` namespace.

    The ``gp-sphinx-`` prefix identifies these classes as part of the
    gp-sphinx workspace.  The badge block (``gp-sphinx-badge``) and its
    sibling blocks (``gp-sphinx-badge-group``, ``gp-sphinx-toolbar``) are
    tier-A shared concepts — any extension may consume them directly,
    and the theme may restyle them once for every consumer.

    Covers both structural variants (size, outline, icon-only) and the
    unified semantic colour palette from ``sab_palettes.css`` (filename
    is historical).

    All consuming ``sphinx-autodoc-*`` packages use these constants for
    shared badge primitives (group, badge, toolbar, type, modifier,
    state classes).  Extension-specific layout and semantic classes
    live under each package's own namespace (e.g.
    ``gp-sphinx-fastmcp__*`` for FastMCP tool sections,
    ``gp-sphinx-pytest-fixtures__*`` for fixture-index layout).

    Examples
    --------
    >>> SAB.PREFIX
    'gp-sphinx-badge'

    >>> SAB.OUTLINE
    'gp-sphinx-badge--outline'

    >>> SAB.TYPE_METHOD
    'gp-sphinx-badge--type-method'

    >>> SAB.STATE_AUTOUSE
    'gp-sphinx-badge--state-autouse'
    """

    PREFIX = "gp-sphinx-badge"

    # ── Structural / layout blocks ───────────────────────
    BADGE = "gp-sphinx-badge"
    BADGE_GROUP = "gp-sphinx-badge-group"
    TOOLBAR = "gp-sphinx-toolbar"

    # Inner label span (BEM element on badge)
    BADGE_LABEL = "gp-sphinx-badge__label"

    # ── Badge variants ───────────────────────────────────
    ICON_ONLY = "gp-sphinx-badge--icon-only"
    INLINE_ICON = "gp-sphinx-badge--inline-icon"
    OUTLINE = "gp-sphinx-badge--outline"
    FILLED = "gp-sphinx-badge--filled"
    ICON_RIGHT = "gp-sphinx-badge--icon-right"

    # Underline control (compose with dense or any badge)
    NO_UNDERLINE = "gp-sphinx-badge--underline-none"
    UNDERLINE_DOTTED = "gp-sphinx-badge--underline-dotted"
    UNDERLINE_SOLID = "gp-sphinx-badge--underline-solid"

    # Size axis
    XXS = "gp-sphinx-badge--size-xxs"
    XS = "gp-sphinx-badge--size-xs"
    SM = "gp-sphinx-badge--size-sm"
    MD = "gp-sphinx-badge--size-md"
    LG = "gp-sphinx-badge--size-lg"
    XL = "gp-sphinx-badge--size-xl"

    # Dense variant (compact, always-bordered, dotted-underline)
    DENSE = "gp-sphinx-badge--dense"

    # ── Python API type badges (filled) ──────────────────
    TYPE_FUNCTION = "gp-sphinx-badge--type-function"
    TYPE_CLASS = "gp-sphinx-badge--type-class"
    TYPE_METHOD = "gp-sphinx-badge--type-method"
    TYPE_PROPERTY = "gp-sphinx-badge--type-property"
    TYPE_ATTRIBUTE = "gp-sphinx-badge--type-attribute"
    TYPE_DATA = "gp-sphinx-badge--type-data"
    TYPE_EXCEPTION = "gp-sphinx-badge--type-exception"
    TYPE_TYPEALIAS = "gp-sphinx-badge--type-typealias"
    TYPE_MODULE = "gp-sphinx-badge--type-module"

    # Slot markers (filled / outlined) for Python API badges
    BADGE_TYPE = "gp-sphinx-badge--slot-type"
    BADGE_MOD = "gp-sphinx-badge--slot-mod"

    # ── Python API modifier badges (outlined) ────────────
    MOD_ASYNC = "gp-sphinx-badge--mod-async"
    MOD_CLASSMETHOD = "gp-sphinx-badge--mod-classmethod"
    MOD_STATICMETHOD = "gp-sphinx-badge--mod-staticmethod"
    MOD_ABSTRACT = "gp-sphinx-badge--mod-abstract"
    MOD_FINAL = "gp-sphinx-badge--mod-final"

    # Sphinx config rebuild-mode badge (outlined)
    MOD_REBUILD = "gp-sphinx-badge--mod-rebuild"

    # ── Shared deprecated state ───────────────────────────
    STATE_DEPRECATED = "gp-sphinx-badge--state-deprecated"

    # ── pytest fixture type (filled green) ───────────────
    TYPE_FIXTURE = "gp-sphinx-badge--type-fixture"

    # Slot markers for fixture badges
    BADGE_FIXTURE = "gp-sphinx-badge--slot-fixture"
    BADGE_SCOPE = "gp-sphinx-badge--slot-scope"
    BADGE_KIND = "gp-sphinx-badge--slot-kind"
    BADGE_STATE = "gp-sphinx-badge--slot-state"

    # ── pytest fixture scopes (filled) ───────────────────
    SCOPE_SESSION = "gp-sphinx-badge--scope-session"
    SCOPE_MODULE = "gp-sphinx-badge--scope-module"
    SCOPE_CLASS = "gp-sphinx-badge--scope-class"

    # ── pytest fixture kinds / states (outlined) ─────────
    STATE_FACTORY = "gp-sphinx-badge--state-factory"
    STATE_OVERRIDE = "gp-sphinx-badge--state-override"
    STATE_AUTOUSE = "gp-sphinx-badge--state-autouse"

    # ── Sphinx config (filled amber) ─────────────────────
    TYPE_CONFIG = "gp-sphinx-badge--type-config"

    # ── docutils (filled violet) ─────────────────────────
    TYPE_DIRECTIVE = "gp-sphinx-badge--type-directive"
    TYPE_ROLE = "gp-sphinx-badge--type-role"
    TYPE_OPTION = "gp-sphinx-badge--type-option"

    # ── Package metadata (maturity + links) ───────────────
    META_ALPHA = "gp-sphinx-badge--meta-alpha"
    META_BETA = "gp-sphinx-badge--meta-beta"
    META_LINK = "gp-sphinx-badge--meta-link"

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
            CSS class string, e.g. ``"gp-sphinx-badge--type-function"``.

        Examples
        --------
        >>> SAB.obj_type("method")
        'gp-sphinx-badge--type-method'

        >>> SAB.obj_type("exception")
        'gp-sphinx-badge--type-exception'
        """
        return f"gp-sphinx-badge--type-{name}"

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
            CSS class string, e.g. ``"gp-sphinx-badge--scope-session"``.

        Examples
        --------
        >>> SAB.scope("session")
        'gp-sphinx-badge--scope-session'

        >>> SAB.scope("module")
        'gp-sphinx-badge--scope-module'
        """
        return f"gp-sphinx-badge--scope-{name}"
