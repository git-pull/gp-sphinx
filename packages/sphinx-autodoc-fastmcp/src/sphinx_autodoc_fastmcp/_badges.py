"""Badge helpers for sphinx_autodoc_fastmcp (thin wrappers over shared API)."""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_autodoc_fastmcp._models import DEFAULT_SAFETY_TIERS, SafetyTier
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
_ACTIVE_TIERS: tuple[SafetyTier, ...] = DEFAULT_SAFETY_TIERS


def use_safety_tiers(tiers: t.Sequence[SafetyTier] | None) -> None:
    """Install the vocabulary badges render from.

    Parameters
    ----------
    tiers : sequence of SafetyTier or None
        Vocabulary for this build. ``None`` restores the default.
    """
    global _ACTIVE_TIERS
    _ACTIVE_TIERS = DEFAULT_SAFETY_TIERS if tiers is None else tuple(tiers)


def _tier(safety: str) -> SafetyTier | None:
    """Return the active tier named ``safety``, or ``None``."""
    return next((tier for tier in _ACTIVE_TIERS if tier.tag == safety), None)


def _safety_spec(safety: str) -> BadgeSpec:
    """Return the badge spec for a tier, honouring the active vocabulary."""
    tier = _tier(safety)
    return BadgeSpec(
        safety,
        tooltip=(tier.tooltip if tier and tier.tooltip else f"Safety: {safety}"),
        icon=(tier.icon if tier else ""),
        classes=(
            SAB.DENSE,
            SAB.NO_UNDERLINE,
            _CSS.BADGE_SAFETY,
            _CSS.safety_class(safety),
        ),
    )


_TYPE_TOOLTIP = "MCP tool"


def build_safety_badge(
    safety: str,
    *,
    icon_only: bool = False,
) -> BadgeNode:
    """Build a safety tier badge.

    Parameters
    ----------
    safety : str
        One of ``readonly``, ``mutating``, ``destructive``.
    icon_only : bool
        When True, create an icon-only badge (empty text, 16x16 colored box).

    Returns
    -------
    BadgeNode

    Examples
    --------
    >>> b = build_safety_badge("readonly")
    >>> b.astext()
    'readonly'
    """
    spec = _safety_spec(safety)
    style: t.Literal["full", "icon-only", "inline-icon"] = (
        "icon-only" if icon_only else "full"
    )
    return build_badge(
        "" if icon_only else safety,
        tooltip=spec.tooltip,
        icon=spec.icon,
        classes=list(spec.classes),
        style=style,
    )


def build_type_tool_badge() -> BadgeNode:
    """Rightmost type badge labeling the entry as an MCP tool.

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


def build_tool_badge_group(safety: str) -> nodes.inline:
    """Badge group: safety tier + type ``tool``.

    Parameters
    ----------
    safety : str
        Safety tier name.

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
    if safety:
        specs.append(_safety_spec(safety))
    specs.append(
        BadgeSpec(
            "tool",
            tooltip=_TYPE_TOOLTIP,
            classes=(SAB.DENSE, SAB.NO_UNDERLINE, SAB.BADGE_TYPE, _CSS.TYPE_TOOL),
        )
    )
    return build_badge_group_from_specs(specs)


def build_toolbar(safety: str) -> nodes.inline:
    """Toolbar on the title row (flex ``margin-left: auto``).

    Examples
    --------
    >>> t = build_toolbar("readonly")
    >>> "gp-sphinx-toolbar" in t["classes"]
    True
    """
    return _sab_build_toolbar(build_tool_badge_group(safety))


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
