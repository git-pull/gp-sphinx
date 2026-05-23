"""Shared CSS class name constants for sphinx_ux_tabs.

Examples
--------
>>> SUT.TABS
'gp-sphinx-tabs'

>>> SUT.INPUT
'gp-sphinx-tabs__input'

>>> SUT.LABEL
'gp-sphinx-tabs__label'

>>> SUT.PANEL
'gp-sphinx-tabs__panel'

>>> SUT.SET_NAME_PREFIX
'gp-sphinx-tab-set-'

>>> SUT.input_id(0, 1)
'gp-sphinx-tab-set-0-input-1'

>>> SUT.set_name(3)
'gp-sphinx-tab-set-3'
"""

from __future__ import annotations


class SUT:
    """CSS class constants for sphinx_ux_tabs under the ``gp-sphinx-`` namespace.

    Tier-B package-owned BEM classes (``gp-sphinx-tabs__input``,
    ``gp-sphinx-tabs__label``, …) carry the radio-input tab structure.
    Tier-A modifier classes follow the ``--axis-value`` convention.

    Examples
    --------
    >>> SUT.TABS
    'gp-sphinx-tabs'

    >>> SUT.LABEL
    'gp-sphinx-tabs__label'
    """

    # Container that holds the radio-input + label + panel triples.
    TABS = "gp-sphinx-tabs"

    # Per-tab elements.
    INPUT = "gp-sphinx-tabs__input"
    LABEL = "gp-sphinx-tabs__label"
    PANEL = "gp-sphinx-tabs__panel"

    # Prefix used to build per-tab-set radio ``name`` and id values so that
    # input/label associations stay scoped to a single tab group.
    SET_NAME_PREFIX = "gp-sphinx-tab-set-"

    @staticmethod
    def set_name(set_index: int) -> str:
        """Return the unique radio ``name`` for tab set ``set_index``.

        Parameters
        ----------
        set_index : int
            Document-wide tab-set counter, starting at ``0``.

        Returns
        -------
        str
            Radio group name, e.g. ``"gp-sphinx-tab-set-0"``.

        Examples
        --------
        >>> SUT.set_name(0)
        'gp-sphinx-tab-set-0'

        >>> SUT.set_name(5)
        'gp-sphinx-tab-set-5'
        """
        return f"{SUT.SET_NAME_PREFIX}{set_index}"

    @staticmethod
    def input_id(set_index: int, item_index: int) -> str:
        """Return the unique ``id`` for the radio input of one tab.

        Parameters
        ----------
        set_index : int
            Document-wide tab-set counter, starting at ``0``.
        item_index : int
            Per-set tab index, starting at ``0``.

        Returns
        -------
        str
            DOM ``id`` of the radio input.

        Examples
        --------
        >>> SUT.input_id(0, 0)
        'gp-sphinx-tab-set-0-input-0'

        >>> SUT.input_id(2, 3)
        'gp-sphinx-tab-set-2-input-3'
        """
        return f"{SUT.SET_NAME_PREFIX}{set_index}-input-{item_index}"
