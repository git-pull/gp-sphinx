"""Badge group rendering helpers for sphinx_autodoc_api_style.

Uses shared ``BadgeNode`` from ``sphinx_ux_badges`` instead of
``nodes.abbreviation`` -- avoids global abbreviation visitor override.

Examples
--------
>>> group = build_badge_group("function", modifiers=frozenset())
>>> "gp-sphinx-badge-group" in group["classes"]
True
"""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_ux_badges import SAB, BadgeSpec, build_badge_group_from_specs

_TYPE_TOOLTIPS: dict[str, str] = {
    "function": "Python function",
    "class": "Python class",
    "method": "Instance method",
    "classmethod": "Class method",
    "staticmethod": "Static method",
    "property": "Python property",
    "attribute": "Class or instance attribute",
    "data": "Module-level data",
    "exception": "Exception class",
    "type": "Type alias",
    "module": "Python module",
}

_TYPE_LABELS: dict[str, str] = {
    "function": "function",
    "class": "class",
    "method": "method",
    "classmethod": "method",
    "staticmethod": "method",
    "property": "property",
    "attribute": "attribute",
    "data": "data",
    "exception": "exception",
    "type": "type",
    "module": "module",
}

_MOD_TOOLTIPS: dict[str, str] = {
    "async": "Asynchronous \u2014 returns a coroutine",
    "classmethod": "Class method \u2014 receives cls as first argument",
    "staticmethod": "Static method \u2014 no implicit self or cls",
    "abstract": "Abstract \u2014 must be overridden in subclasses",
    "final": "Final \u2014 cannot be overridden in subclasses",
    "deprecated": "Deprecated \u2014 see docs for replacement",
}

_MOD_CSS: dict[str, str] = {
    "async": SAB.MOD_ASYNC,
    "classmethod": SAB.MOD_CLASSMETHOD,
    "staticmethod": SAB.MOD_STATICMETHOD,
    "abstract": SAB.MOD_ABSTRACT,
    "final": SAB.MOD_FINAL,
    "deprecated": SAB.STATE_DEPRECATED,
}

_MOD_LABELS: dict[str, str] = {
    "async": "async",
    "classmethod": "classmethod",
    "staticmethod": "staticmethod",
    "abstract": "abstract",
    "final": "final",
    "deprecated": "deprecated",
}

_MOD_ORDER: tuple[str, ...] = (
    "deprecated",
    "abstract",
    "final",
    "async",
    "classmethod",
    "staticmethod",
)


def build_badge_group(
    objtype: str,
    *,
    modifiers: frozenset[str],
    show_type_badge: bool = True,
) -> nodes.inline:
    """Return a badge group for a Python API entry.

    Badge slots (left-to-right in visual order):

    * Slots 0\u2013N (modifiers): ``deprecated``, ``abstract``, ``final``,
      ``async``, ``classmethod``, ``staticmethod`` \u2014 in fixed order.
    * Final slot (type): ``function``, ``class``, ``method``, etc.

    Parameters
    ----------
    objtype : str
        Python domain object type (``"function"``, ``"class"``, etc.).
    modifiers : frozenset[str]
        Active modifier names (e.g. ``{"async", "abstract"}``).
    show_type_badge : bool
        When ``False``, suppress the type badge at the rightmost slot.

    Returns
    -------
    nodes.inline
        Badge group container with BadgeNode children.

    Examples
    --------
    >>> group = build_badge_group("function", modifiers=frozenset())
    >>> "gp-sphinx-badge-group" in group["classes"]
    True

    >>> group = build_badge_group("method", modifiers=frozenset({"async"}))
    >>> from sphinx_ux_badges import BadgeNode
    >>> len(list(group.findall(BadgeNode))) == 2
    True

    >>> group = build_badge_group(
    ...     "class",
    ...     modifiers=frozenset({"abstract", "deprecated"}),
    ... )
    >>> from sphinx_ux_badges import BadgeNode
    >>> labels = [n.astext() for n in group.findall(BadgeNode)]
    >>> "deprecated" in labels and "abstract" in labels and "class" in labels
    True
    """
    badge_specs: list[BadgeSpec] = []

    for mod in _MOD_ORDER:
        if mod not in modifiers:
            continue
        fill: t.Literal["filled", "outline"] = (
            "filled" if mod == "deprecated" else "outline"
        )
        badge_specs.append(
            BadgeSpec(
                _MOD_LABELS[mod],
                tooltip=_MOD_TOOLTIPS[mod],
                classes=(SAB.BADGE, SAB.BADGE_MOD, _MOD_CSS[mod]),
                fill=fill,
            )
        )

    if show_type_badge:
        label = _TYPE_LABELS.get(objtype, objtype)
        tooltip = _TYPE_TOOLTIPS.get(objtype, f"Python {objtype}")
        badge_specs.append(
            BadgeSpec(
                label,
                tooltip=tooltip,
                classes=(SAB.BADGE, SAB.BADGE_TYPE, SAB.obj_type(objtype)),
            )
        )

    return build_badge_group_from_specs(badge_specs, classes=[SAB.BADGE_GROUP])
