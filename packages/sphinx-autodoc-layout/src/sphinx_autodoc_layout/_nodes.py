"""Custom docutils nodes for autodoc layout regions.

Two generic nodes cover the full component tree:

- ``gal_region`` wraps contiguous runs of ``desc_content`` children
  (narrative paragraphs, field lists, nested members).
- ``gal_fold`` wraps a region in ``<details>/<summary>`` for
  progressive disclosure of large parameter sections.
- ``gal_sig_fold`` wraps a ``desc_parameterlist`` in
  ``<details>/<summary>`` for inline signature disclosure.

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


class gal_sig_fold(nodes.General, nodes.Element):
    """Inline disclosure wrapper for ``desc_parameterlist`` in signatures.

    Wraps the parameter list in ``<details>/<summary>`` so the
    collapsed state shows the first parameter plus ``[...]`` and
    expanding reveals the full list one-per-line.

    Parameters
    ----------
    first_param : str
        Text of the first parameter (shown in collapsed summary).
    param_count : int
        Total number of parameters.

    Examples
    --------
    >>> sf = gal_sig_fold(first_param="host", param_count=13)
    >>> sf.get("first_param")
    'host'
    >>> sf.get("param_count")
    13
    """
