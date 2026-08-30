"""Badge helpers for sphinx_autodoc_fastmcp (thin wrappers over shared API)."""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_autodoc_fastmcp._models import DEFAULT_TOOLSETS, Toolset
from sphinx_ux_badges import (
    SAB,
    BadgeNode,
    BadgeSpec,
    build_badge,
    build_badge_group_from_specs,
    build_toolbar as _sab_build_toolbar,
)

#: Vocabulary in force for the current build. Badges are built from
#: several call sites that have no ``app`` in scope, so the extension
#: installs it once at ``builder-inited`` rather than threading it
#: through every one.
_ACTIVE_TOOLSETS: tuple[Toolset, ...] = DEFAULT_TOOLSETS


def use_toolsets(toolsets: t.Sequence[Toolset] | None) -> None:
    """Install the vocabulary badges render from.

    Parameters
    ----------
    toolsets : sequence of Toolset or None
        Vocabulary for this build. ``None`` restores the default.
    """
    global _ACTIVE_TOOLSETS
    _ACTIVE_TOOLSETS = DEFAULT_TOOLSETS if toolsets is None else tuple(toolsets)


def _declared(toolset: str) -> Toolset | None:
    """Return the active toolset named ``toolset``, or ``None``."""
    return next((entry for entry in _ACTIVE_TOOLSETS if entry.tag == toolset), None)


def active_toolsets() -> tuple[Toolset, ...]:
    """Return the vocabulary in force, in the order it was declared."""
    return _ACTIVE_TOOLSETS


def _toolset_spec(toolset: str) -> BadgeSpec:
    """Return the badge spec for a toolset, honouring the active vocabulary."""
    entry = _declared(toolset)
    return BadgeSpec(
        toolset,
        tooltip=(entry.tooltip if entry and entry.tooltip else f"Toolset: {toolset}"),
        icon=(entry.icon if entry else ""),
        classes=(
            SAB.DENSE,
            SAB.NO_UNDERLINE,
            _CSS.BADGE_TOOLSET,
            _CSS.toolset_class(toolset),
            _CSS.tone_class(entry.tone if entry else "slate"),
        ),
    )


_TYPE_TOOLTIP = "MCP tool"


def build_toolset_badge(
    toolset: str,
    *,
    icon_only: bool = False,
) -> BadgeNode:
    """Build a toolset badge.

    Parameters
    ----------
    toolset : str
        A tag from the project's ``fastmcp_toolsets``. A tag outside it
        still renders, untinted and claiming nothing.
    icon_only : bool
        When True, create an icon-only badge (empty text, 16x16 colored box).

    Returns
    -------
    BadgeNode

    Examples
    --------
    >>> b = build_toolset_badge("readonly")
    >>> b.astext()
    'readonly'
    """
    spec = _toolset_spec(toolset)
    style: t.Literal["full", "icon-only", "inline-icon"] = (
        "icon-only" if icon_only else "full"
    )
    return build_badge(
        "" if icon_only else toolset,
        tooltip=spec.tooltip,
        icon=spec.icon,
        classes=list(spec.classes),
        style=style,
    )


def build_type_tool_badge() -> BadgeNode:
    """Rightmost type badge labeling the component as an MCP tool.

    Examples
    --------
    >>> b = build_type_tool_badge()
    >>> b.astext()
    'tool'
    """
    return build_badge(
        "tool",
        tooltip=_TYPE_TOOLTIP,
        classes=[SAB.DENSE, SAB.NO_UNDERLINE, SAB.BADGE_TYPE, _CSS.TYPE_TOOL],
    )


def build_tool_badge_group(toolset: str) -> nodes.inline:
    """Badge group: toolset entry + type ``tool``.

    Parameters
    ----------
    toolset : str
        Toolset tag name.

    Returns
    -------
    nodes.inline

    Examples
    --------
    >>> g = build_tool_badge_group("readonly")
    >>> "gp-sphinx-badge-group" in g["classes"]
    True
    """
    specs: list[BadgeSpec] = []
    if toolset:
        specs.append(_toolset_spec(toolset))
    specs.append(
        BadgeSpec(
            "tool",
            tooltip=_TYPE_TOOLTIP,
            classes=(SAB.DENSE, SAB.NO_UNDERLINE, SAB.BADGE_TYPE, _CSS.TYPE_TOOL),
        )
    )
    return build_badge_group_from_specs(specs)


def build_toolbar(toolset: str) -> nodes.inline:
    """Toolbar on the title row (flex ``margin-left: auto``).

    Examples
    --------
    >>> t = build_toolbar("readonly")
    >>> "gp-sphinx-toolbar" in t["classes"]
    True
    """
    return _sab_build_toolbar(build_tool_badge_group(toolset))


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
