"""HTML visitors for layout nodes.

Each node maps to a simple wrapper element:

- ``gal_region`` -> ``<div class="gal-region gal-region--{kind}">``
- ``gal_fold``   -> ``<details class="gal-fold ..."><summary>...</summary>``

Non-HTML builders get passthrough visitors that render children
without any wrapper markup.

Examples
--------
>>> callable(visit_gal_region)
True
>>> callable(depart_gal_region)
True
>>> callable(visit_gal_fold)
True
>>> callable(depart_gal_fold)
True
"""

from __future__ import annotations

import typing as t

from docutils import nodes

if t.TYPE_CHECKING:
    from sphinx.writers.html5 import HTML5Translator


# -- HTML visitors -----------------------------------------------------------


def visit_gal_region(self: HTML5Translator, node: nodes.Element) -> None:
    """Open a region wrapper ``<div>``."""
    kind = node.get("kind", "narrative")
    self.body.append(f'<div class="gal-region gal-region--{kind}">')


def depart_gal_region(self: HTML5Translator, node: nodes.Element) -> None:
    """Close the region ``<div>``."""
    self.body.append("</div>")


def visit_gal_fold(self: HTML5Translator, node: nodes.Element) -> None:
    """Open a ``<details>`` disclosure element."""
    summary = node.get("summary", "")
    kind = node.get("kind", "")
    open_attr = " open" if node.get("open", False) else ""
    self.body.append(
        f'<details class="gal-fold gal-fold--{kind}"{open_attr}>'
        f'<summary class="gal-fold-summary">{summary}</summary>'
    )


def depart_gal_fold(self: HTML5Translator, node: nodes.Element) -> None:
    """Close the ``</details>`` element."""
    self.body.append("</details>")


# -- Passthrough visitors (non-HTML builders) --------------------------------


def passthrough_visit(self: t.Any, node: nodes.Element) -> None:
    """No-op visit for non-HTML builders.

    Examples
    --------
    >>> passthrough_visit(None, None)
    """


def passthrough_depart(self: t.Any, node: nodes.Element) -> None:
    """No-op depart for non-HTML builders.

    Examples
    --------
    >>> passthrough_depart(None, None)
    """
