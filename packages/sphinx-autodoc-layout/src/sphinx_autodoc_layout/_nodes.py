"""Custom docutils nodes for autodoc layout regions.

Two generic nodes cover the full component tree:

- ``gal_region`` wraps contiguous runs of ``desc_content`` children
  (narrative paragraphs, field lists, nested members).
- ``gal_fold`` wraps a region in ``<details>/<summary>`` for
  progressive disclosure of large parameter sections.

Examples
--------
>>> from sphinx_autodoc_layout._nodes import gal_region, gal_fold
>>> r = gal_region(kind="fields")
>>> r.get("kind")
'fields'

>>> f = gal_fold(kind="parameters", summary="Parameters (5)")
>>> f.get("summary")
'Parameters (5)'
"""

from __future__ import annotations

from docutils import nodes


class gal_region(nodes.General, nodes.Element):
    """Wrapper for a contiguous ``desc_content`` run.

    Parameters
    ----------
    kind : str
        One of ``"narrative"``, ``"fields"``, or ``"members"``.

    Examples
    --------
    >>> r = gal_region(kind="narrative")
    >>> isinstance(r, gal_region)
    True
    >>> r.get("kind")
    'narrative'
    """


class gal_fold(nodes.General, nodes.Element):
    """Block disclosure wrapper rendered as ``<details>/<summary>``.

    Parameters
    ----------
    kind : str
        Fold category, e.g. ``"parameters"``.
    summary : str
        Text shown in the ``<summary>`` element.
    open : bool
        Whether the fold starts expanded.

    Examples
    --------
    >>> f = gal_fold(kind="parameters", summary="Parameters (3)")
    >>> f.get("kind")
    'parameters'
    >>> f.get("summary")
    'Parameters (3)'
    """
