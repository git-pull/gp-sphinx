"""Shared CSS class name constants for sphinx_ux_grid.

Examples
--------
>>> SUG.GRID
'gp-sphinx-grid'

>>> SUG.ITEM
'gp-sphinx-grid__item'

>>> SUG.CARD
'gp-sphinx-grid-card'

>>> SUG.CARD_BODY
'gp-sphinx-grid-card__body'

>>> SUG.CARD_TITLE
'gp-sphinx-grid-card__title'

>>> SUG.CARD_HEADER
'gp-sphinx-grid-card__header'

>>> SUG.CARD_FOOTER
'gp-sphinx-grid-card__footer'

>>> SUG.CARD_IMG_TOP
'gp-sphinx-grid-card__img-top'

>>> SUG.CARD_IMG_BOTTOM
'gp-sphinx-grid-card__img-bottom'

>>> SUG.OUTLINE
'gp-sphinx-grid-card--outline'

>>> SUG.REVERSE
'gp-sphinx-grid--reverse'

>>> SUG.shadow('md')
'gp-sphinx-grid-card--shadow-md'
"""

from __future__ import annotations


class SUG:
    """CSS class constants for sphinx_ux_grid under the ``gp-sphinx-`` namespace.

    Tier-B package-owned BEM classes (``gp-sphinx-grid__item``,
    ``gp-sphinx-grid-card__body``, …) carry the grid's layout.  Modifier
    classes (``gp-sphinx-grid-card--shadow-md``) follow the axis-value
    modifier convention shared with the rest of the workspace.

    Examples
    --------
    >>> SUG.GRID
    'gp-sphinx-grid'

    >>> SUG.CARD_BODY
    'gp-sphinx-grid-card__body'

    >>> SUG.shadow('lg')
    'gp-sphinx-grid-card--shadow-lg'

    >>> SUG.text_align('center')
    'gp-sphinx-grid-card--text-center'
    """

    # ── Grid container & item ────────────────────────────
    GRID = "gp-sphinx-grid"
    ITEM = "gp-sphinx-grid__item"
    REVERSE = "gp-sphinx-grid--reverse"
    OUTLINE_GRID = "gp-sphinx-grid--outline"
    OUTLINE_ITEM = "gp-sphinx-grid__item--outline"

    # ── Card block ───────────────────────────────────────
    CARD = "gp-sphinx-grid-card"
    CARD_BODY = "gp-sphinx-grid-card__body"
    CARD_TITLE = "gp-sphinx-grid-card__title"
    CARD_HEADER = "gp-sphinx-grid-card__header"
    CARD_FOOTER = "gp-sphinx-grid-card__footer"
    CARD_IMG_TOP = "gp-sphinx-grid-card__img-top"
    CARD_IMG_BOTTOM = "gp-sphinx-grid-card__img-bottom"
    CARD_IMG_BACKGROUND = "gp-sphinx-grid-card__img-background"
    CARD_IMG_OVERLAY = "gp-sphinx-grid-card__overlay"
    CARD_LINK = "gp-sphinx-grid-card__link"
    CARD_HOVER = "gp-sphinx-grid-card--hover"
    OUTLINE = "gp-sphinx-grid-card--outline"

    @staticmethod
    def shadow(level: str) -> str:
        """Return the shadow-modifier CSS class for ``level``.

        Parameters
        ----------
        level : str
            Shadow level — ``"sm"``, ``"md"``, or ``"lg"``.  ``"none"``
            returns an empty string (no modifier applied).

        Returns
        -------
        str
            CSS class string, e.g. ``"gp-sphinx-grid-card--shadow-sm"``.
            Empty string when ``level == "none"``.

        Examples
        --------
        >>> SUG.shadow('sm')
        'gp-sphinx-grid-card--shadow-sm'

        >>> SUG.shadow('none')
        ''
        """
        if level == "none":
            return ""
        return f"gp-sphinx-grid-card--shadow-{level}"

    @staticmethod
    def text_align(value: str) -> str:
        """Return the text-align modifier CSS class for ``value``.

        Parameters
        ----------
        value : str
            Alignment value — ``"left"``, ``"right"``, ``"center"``,
            or ``"justify"``.

        Returns
        -------
        str
            CSS class string, e.g. ``"gp-sphinx-grid-card--text-center"``.

        Examples
        --------
        >>> SUG.text_align('left')
        'gp-sphinx-grid-card--text-left'
        """
        return f"gp-sphinx-grid-card--text-{value}"

    @staticmethod
    def item_direction(value: str) -> str:
        """Return the ``gp-sphinx-grid__item--direction-<value>`` modifier class.

        Parameters
        ----------
        value : str
            Direction value — ``"row"`` or ``"column"``.

        Returns
        -------
        str
            CSS class string, e.g. ``"gp-sphinx-grid__item--direction-row"``.

        Examples
        --------
        >>> SUG.item_direction('row')
        'gp-sphinx-grid__item--direction-row'
        """
        return f"gp-sphinx-grid__item--direction-{value}"

    @staticmethod
    def item_align(value: str) -> str:
        """Return the ``gp-sphinx-grid__item--align-<value>`` modifier class.

        Parameters
        ----------
        value : str
            Alignment value — ``"start"``, ``"end"``, ``"center"``,
            ``"justify"``, or ``"spaced"``.

        Returns
        -------
        str
            CSS class string, e.g. ``"gp-sphinx-grid__item--align-center"``.

        Examples
        --------
        >>> SUG.item_align('center')
        'gp-sphinx-grid__item--align-center'
        """
        return f"gp-sphinx-grid__item--align-{value}"

    @staticmethod
    def width(value: str) -> str:
        """Return the width modifier CSS class for ``value``.

        Parameters
        ----------
        value : str
            Width value — ``"auto"``, ``"25%"``, ``"50%"``, ``"75%"``,
            or ``"100%"``.  The trailing ``%`` is stripped.

        Returns
        -------
        str
            CSS class string, e.g. ``"gp-sphinx-grid-card--width-50"``.

        Examples
        --------
        >>> SUG.width('50%')
        'gp-sphinx-grid-card--width-50'

        >>> SUG.width('auto')
        'gp-sphinx-grid-card--width-auto'
        """
        return f"gp-sphinx-grid-card--width-{value.rstrip('%')}"
