"""CSS class name constants for sphinx_ux_autodoc_layout.

All constants use the ``gp-sphinx-api-`` namespace for shared layout
primitives (cards, regions, sections, folds, signatures).  Every domain
package consuming the layout transforms emits these classes, so the
theme can style them once.

Examples
--------
>>> API.CONTAINER
'gp-sphinx-api-container'

>>> API.HEADER
'gp-sphinx-api-header'

>>> API.SIGNATURE_TOGGLE
'gp-sphinx-api-signature-toggle'

>>> API.PROFILE_PREFIX
'gp-sphinx-api-profile'
"""

from __future__ import annotations


class API:
    """CSS class name constants (``gp-sphinx-api-`` namespace)."""

    PREFIX = "gp-sphinx-api"

    # ── Card / container primitives ──────────────────────
    CONTAINER = "gp-sphinx-api-container"
    CARD_SHELL = "gp-sphinx-api-card-shell"
    CARD_ENTRY = "gp-sphinx-api-card-entry"
    ENTRY = "gp-sphinx-api-entry"

    # ── Structural elements inside a card ────────────────
    HEADER = "gp-sphinx-api-header"
    CONTENT = "gp-sphinx-api-content"
    LAYOUT = "gp-sphinx-api-layout"
    # Desktop variant: signature-left, toolbar-right (single row, ≥ 52rem)
    LAYOUT_DESKTOP = "gp-sphinx-api-layout--desktop"
    # Mobile variant: toolbar-top, signature-bottom (stacked, < 52rem)
    LAYOUT_MOBILE = "gp-sphinx-api-layout--mobile"
    # Desktop slots (horizontal axis)
    LAYOUT_LEFT = "gp-sphinx-api-layout-left"
    LAYOUT_RIGHT = "gp-sphinx-api-layout-right"
    # Mobile slots (vertical axis): toolbar above, signature below
    LAYOUT_TOP = "gp-sphinx-api-layout-top"
    LAYOUT_BOTTOM = "gp-sphinx-api-layout-bottom"
    SIGNATURE = "gp-sphinx-api-signature"
    LINK = "gp-sphinx-api-link"
    BADGE_CONTAINER = "gp-sphinx-api-badge-container"
    SOURCE_LINK = "gp-sphinx-api-source-link"

    # ── Header boolean modifiers (mirrored as data-has-*) ─
    # Each modifier doubles a corresponding data-has-<name> attribute on
    # the rendered <dt>; CSS can target either selector form.
    HEADER_HAS_SOURCE = "gp-sphinx-api-header--has-source"
    HEADER_HAS_BADGES = "gp-sphinx-api-header--has-badges"
    HEADER_HAS_FOLD = "gp-sphinx-api-header--has-fold"

    # ── Signature expand/collapse (long signatures) ──────
    SIGNATURE_TOGGLE = "gp-sphinx-api-signature-toggle"
    SIGNATURE_PREVIEW = "gp-sphinx-api-signature-preview"
    SIGNATURE_EXPANDED = "gp-sphinx-api-signature-expanded"
    SIG_TOGGLE = "gp-sphinx-api-sig-toggle"
    SIG_PREVIEW = "gp-sphinx-api-sig-preview"
    SIG_EXPANDED = "gp-sphinx-api-sig-expanded"
    SIG_COLLAPSE = "gp-sphinx-api-sig-collapse"

    # ── Content sections (closed enum) ───────────────────
    DESCRIPTION = "gp-sphinx-api-description"
    FACTS = "gp-sphinx-api-facts"
    FACTS_LIST = "gp-sphinx-api-facts-list"
    SUMMARY = "gp-sphinx-api-summary"
    PARAMETERS = "gp-sphinx-api-parameters"
    OPTIONS = "gp-sphinx-api-options"
    FOOTER = "gp-sphinx-api-footer"

    # ── Region primitive (BEM block with modifier axis) ──
    REGION = "gp-sphinx-api-region"

    # ── Disclosure (parameter folding) ───────────────────
    FOLD = "gp-sphinx-api-fold"
    FOLD_SUMMARY = "gp-sphinx-api-fold-summary"

    # ── Slot primitive (generic slot nodes in docutils tree) ──
    SLOT = "gp-sphinx-api-slot"

    # ── Dynamic modifier prefixes ────────────────────────
    # Used at call sites as f"{API.PROFILE_PREFIX}--{slug}" etc.
    PROFILE_PREFIX = "gp-sphinx-api-profile"
    REGION_MODIFIER_PREFIX = "gp-sphinx-api-region"  # for f"{PREFIX}--{kind}"
    FOLD_MODIFIER_PREFIX = "gp-sphinx-api-fold"  # for f"{PREFIX}--{kind}"
    SLOT_MODIFIER_PREFIX = "gp-sphinx-api-slot"  # for f"{PREFIX}--{name}"

    @staticmethod
    def profile(slug: str) -> str:
        """Return the profile modifier class for ``slug``.

        Examples
        --------
        >>> API.profile("py-function")
        'gp-sphinx-api-profile--py-function'

        >>> API.profile("fastmcp-tool")
        'gp-sphinx-api-profile--fastmcp-tool'
        """
        return f"gp-sphinx-api-profile--{slug}"

    @staticmethod
    def region_modifier(kind: str) -> str:
        """Return the region modifier class for ``kind``.

        Examples
        --------
        >>> API.region_modifier("fields")
        'gp-sphinx-api-region--fields'

        >>> API.region_modifier("members")
        'gp-sphinx-api-region--members'
        """
        return f"gp-sphinx-api-region--{kind}"

    @staticmethod
    def fold_modifier(kind: str) -> str:
        """Return the fold modifier class for ``kind``.

        Examples
        --------
        >>> API.fold_modifier("parameters")
        'gp-sphinx-api-fold--parameters'
        """
        return f"gp-sphinx-api-fold--{kind}"

    @staticmethod
    def slot_modifier(name: str) -> str:
        """Return the slot modifier class for ``name``.

        Examples
        --------
        >>> API.slot_modifier("badges")
        'gp-sphinx-api-slot--badges'
        """
        return f"gp-sphinx-api-slot--{name}"

    @staticmethod
    def header_modifier(name: str) -> str:
        """Return the header modifier class for ``name``.

        Header modifiers describe styling-relevant metadata (whether the
        signature has a source link, badge count > 0, a fold toggle, ...).
        They mirror ``data-has-<name>`` attributes for selector flexibility.

        Examples
        --------
        >>> API.header_modifier("has-source")
        'gp-sphinx-api-header--has-source'

        >>> API.header_modifier("has-badges")
        'gp-sphinx-api-header--has-badges'
        """
        return f"gp-sphinx-api-header--{name}"

    @staticmethod
    def layout_variant(variant: str) -> str:
        """Return the layout variant modifier class for ``variant``.

        Examples
        --------
        >>> API.layout_variant("desktop")
        'gp-sphinx-api-layout--desktop'

        >>> API.layout_variant("mobile")
        'gp-sphinx-api-layout--mobile'
        """
        return f"gp-sphinx-api-layout--{variant}"
