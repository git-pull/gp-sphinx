"""CSS class name constants for sphinx_autodoc_pytest_fixtures.

All constants use the ``gp-sphinx-pytest-fixtures`` namespace for
fixture-index layout.  Shared badge primitives come from ``SAB`` in
``sphinx-ux-badges``; shared card/region primitives come from ``API`` in
``sphinx-ux-autodoc-layout``.

Examples
--------
>>> SPF.FIXTURE_INDEX
'gp-sphinx-pytest-fixtures__fixture-index'

>>> SPF.TABLE_SCROLL
'gp-sphinx-pytest-fixtures__table-scroll'
"""

from __future__ import annotations


class SPF:
    """CSS class name constants (``gp-sphinx-pytest-fixtures`` namespace)."""

    PREFIX = "gp-sphinx-pytest-fixtures"

    FIXTURE_INDEX = "gp-sphinx-pytest-fixtures__fixture-index"
    TABLE_SCROLL = "gp-sphinx-pytest-fixtures__table-scroll"
    DEPRECATED = "gp-sphinx-pytest-fixtures__deprecated"
