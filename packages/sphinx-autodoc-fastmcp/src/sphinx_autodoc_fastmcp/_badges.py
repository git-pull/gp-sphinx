"""Badge helpers for sphinx_autodoc_fastmcp (thin wrappers over shared API)."""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_autodoc_fastmcp._models import DEFAULT_AXES, Axis
from sphinx_ux_badges import (
    SAB,
    BadgeNode,
    BadgeSpec,
    build_badge,
    build_badge_group_from_specs,
    build_toolbar as _sab_build_toolbar,
)

#: Badges are built from call sites with no ``app`` in scope, so the
#: extension installs the axes once at ``builder-inited``.
_ACTIVE_AXES: tuple[Axis, ...] = DEFAULT_AXES


def use_axes(axes: t.Sequence[Axis] | None) -> None:
    """Install the axes badges render from. ``None`` restores the default."""
    global _ACTIVE_AXES
    _ACTIVE_AXES = DEFAULT_AXES if axes is None else tuple(axes)


def active_axes() -> tuple[Axis, ...]:
    """Return the axes in force, in the order they were declared."""
    return _ACTIVE_AXES


def _axis(name: str) -> Axis | None:
    """Return the active axis called ``name``, or ``None``."""
    return next((a for a in _ACTIVE_AXES if a.name == name), None)


_TYPE_TOOLTIP = "MCP tool"


def term_spec(axis_name: str, value: str) -> BadgeSpec:
    """Return the badge spec for ``value`` on axis ``axis_name``.

    An undeclared axis or term still renders, untinted and claiming
    nothing, so a tag the project forgot to declare is visible rather than
    silently dropped.
    """
    axis = _axis(axis_name)
    term = axis.term(value) if axis else None
    return BadgeSpec(
        term.label if term and term.label else value,
        tooltip=(
            term.tooltip if term and term.tooltip else f"{axis_name.title()}: {value}"
        ),
        icon=(term.icon if term else ""),
        classes=(
            SAB.DENSE,
            SAB.NO_UNDERLINE,
            _CSS.BADGE_TOOLSET,
            _CSS.axis_class(axis_name),
            _CSS.term_class(axis_name, value),
            _CSS.tone_class(term.tone if term else "slate"),
            *(term.classes if term else ()),
        ),
        style=t.cast(
            't.Literal["full", "icon-only", "inline-icon"]',
            term.style if term else "full",
        ),
        fill=t.cast('t.Literal["filled", "outline"]', term.fill if term else "filled"),
    )


def build_axis_badge(
    axis_name: str,
    value: str,
    *,
    icon_only: bool = False,
) -> BadgeNode:
    """Build one axis badge.

    Examples
    --------
    >>> build_axis_badge("risk", "readonly").astext()
    'readonly'
    """
    spec = term_spec(axis_name, value)
    style: t.Literal["full", "icon-only", "inline-icon"] = (
        "icon-only" if icon_only else spec.style
    )
    return build_badge(
        "" if icon_only else spec.text,
        tooltip=spec.tooltip,
        icon=spec.icon,
        classes=list(spec.classes),
        style=style,
        fill=spec.fill,
    )


def build_type_tool_badge() -> BadgeNode:
    """Rightmost type badge labeling the component as an MCP tool.

    Examples
    --------
    >>> build_type_tool_badge().astext()
    'tool'
    """
    return build_badge(
        "tool",
        tooltip=_TYPE_TOOLTIP,
        classes=[SAB.DENSE, SAB.NO_UNDERLINE, SAB.BADGE_TYPE, _CSS.TYPE_TOOL],
    )


def primary_axis(axes: dict[str, str]) -> tuple[str, str] | None:
    """Return the ``(axis, term)`` a single inline badge should show.

    Inline references have room for one badge, so they take the first
    declared axis the tool matched.

    Examples
    --------
    >>> primary_axis({"risk": "readonly"})
    ('risk', 'readonly')
    >>> primary_axis({}) is None
    True
    """
    for axis in _ACTIVE_AXES:
        if axes.get(axis.name):
            return axis.name, axes[axis.name]
    return next(((n, v) for n, v in axes.items() if v), None)


def build_tool_badge_group(axes: dict[str, str]) -> nodes.inline:
    """Badge group: one badge per matched axis, then the type badge.

    Axes render in declaration order, so the group reads the way the
    project ordered its taxonomy.

    Examples
    --------
    >>> g = build_tool_badge_group({"risk": "readonly"})
    >>> "gp-sphinx-badge-group" in g["classes"]
    True
    """
    specs: list[BadgeSpec] = [
        term_spec(axis.name, axes[axis.name])
        for axis in _ACTIVE_AXES
        if axes.get(axis.name)
    ]
    specs.extend(
        term_spec(name, value)
        for name, value in axes.items()
        if value and _axis(name) is None
    )
    specs.append(
        BadgeSpec(
            "tool",
            tooltip=_TYPE_TOOLTIP,
            classes=(SAB.DENSE, SAB.NO_UNDERLINE, SAB.BADGE_TYPE, _CSS.TYPE_TOOL),
        )
    )
    return build_badge_group_from_specs(specs)


def build_toolbar(axes: dict[str, str]) -> nodes.inline:
    """Toolbar on the title row (flex ``margin-left: auto``).

    Examples
    --------
    >>> "gp-sphinx-toolbar" in build_toolbar({"risk": "readonly"})["classes"]
    True
    """
    return _sab_build_toolbar(build_tool_badge_group(axes))


_TYPE_TOOLTIP_PROMPT = "MCP prompt recipe"
_TYPE_TOOLTIP_RESOURCE = "MCP resource (fixed URI)"
_TYPE_TOOLTIP_RESOURCE_TEMPLATE = "MCP resource template (parameterised URI)"


def build_prompt_badge_group(tags: t.Sequence[str] = ()) -> nodes.inline:
    """Badge group: ``prompt`` type + optional tag pills.

    Examples
    --------
    >>> g = build_prompt_badge_group(())
    >>> "gp-sphinx-badge-group" in g["classes"]
    True
    """
    specs = [
        BadgeSpec(
            "prompt",
            tooltip=_TYPE_TOOLTIP_PROMPT,
            classes=(
                SAB.DENSE,
                SAB.NO_UNDERLINE,
                SAB.BADGE_TYPE,
                _CSS.TYPE_PROMPT,
            ),
        ),
    ]
    for tag in tags:
        specs.append(
            BadgeSpec(
                tag,
                tooltip=f"Tag: {tag}",
                classes=(SAB.DENSE, SAB.NO_UNDERLINE, _CSS.BADGE_TAG),
            ),
        )
    return build_badge_group_from_specs(specs)


def build_resource_badge_group(
    mime_type: str,
    tags: t.Sequence[str] = (),
    *,
    kind: t.Literal["resource", "resource-template"] = "resource",
) -> nodes.inline:
    """Badge group for a resource or resource template.

    Emits a type badge (``resource`` or ``resource-template``), an optional
    MIME pill, and optional tag pills.

    Examples
    --------
    >>> g = build_resource_badge_group("application/json")
    >>> "gp-sphinx-badge-group" in g["classes"]
    True
    """
    if kind == "resource-template":
        type_spec = BadgeSpec(
            "resource-template",
            tooltip=_TYPE_TOOLTIP_RESOURCE_TEMPLATE,
            classes=(
                SAB.DENSE,
                SAB.NO_UNDERLINE,
                SAB.BADGE_TYPE,
                _CSS.TYPE_RESOURCE_TEMPLATE,
            ),
        )
    else:
        type_spec = BadgeSpec(
            "resource",
            tooltip=_TYPE_TOOLTIP_RESOURCE,
            classes=(SAB.DENSE, SAB.NO_UNDERLINE, SAB.BADGE_TYPE, _CSS.TYPE_RESOURCE),
        )
    specs = [type_spec]
    if mime_type:
        specs.append(
            BadgeSpec(
                mime_type,
                tooltip=f"MIME type: {mime_type}",
                classes=(SAB.DENSE, SAB.NO_UNDERLINE, _CSS.BADGE_MIME),
            ),
        )
    for tag in tags:
        specs.append(
            BadgeSpec(
                tag,
                tooltip=f"Tag: {tag}",
                classes=(SAB.DENSE, SAB.NO_UNDERLINE, _CSS.BADGE_TAG),
            ),
        )
    return build_badge_group_from_specs(specs)
