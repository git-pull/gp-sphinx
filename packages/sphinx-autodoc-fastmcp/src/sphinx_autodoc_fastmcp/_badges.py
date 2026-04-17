"""Badge helpers for sphinx_autodoc_fastmcp (thin wrappers over shared API)."""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_ux_badges import (
    SAB,
    BadgeNode,
    BadgeSpec,
    build_badge,
    build_badge_group_from_specs,
    build_toolbar as _sab_build_toolbar,
)

_SAFETY_LABELS = ("readonly", "mutating", "destructive")

_SAFETY_TOOLTIPS: dict[str, str] = {
    "readonly": "Read-only \u2014 does not modify external state",
    "mutating": "Mutating \u2014 creates or modifies objects",
    "destructive": "Destructive \u2014 may remove data; not reversible",
}

_SAFETY_ICONS: dict[str, str] = {
    "readonly": "\U0001f50d",
    "mutating": "\u270f\ufe0f",
    "destructive": "\U0001f4a3",
}

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
    label = safety if safety in _SAFETY_LABELS else safety
    text = "" if icon_only else label
    style: t.Literal["full", "icon-only", "inline-icon"] = (
        "icon-only" if icon_only else "full"
    )
    classes = [
        SAB.DENSE,
        SAB.NO_UNDERLINE,
        _CSS.BADGE_SAFETY,
        _CSS.safety_class(safety),
    ]
    return build_badge(
        text,
        tooltip=_SAFETY_TOOLTIPS.get(safety, f"Safety: {safety}"),
        icon=_SAFETY_ICONS.get(safety, ""),
        classes=classes,
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
    return build_badge_group_from_specs(
        [
            BadgeSpec(
                safety if safety in _SAFETY_LABELS else safety,
                tooltip=_SAFETY_TOOLTIPS.get(safety, f"Safety: {safety}"),
                icon=_SAFETY_ICONS.get(safety, ""),
                classes=(
                    SAB.DENSE,
                    SAB.NO_UNDERLINE,
                    _CSS.BADGE_SAFETY,
                    _CSS.safety_class(safety),
                ),
            ),
            BadgeSpec(
                "tool",
                tooltip=_TYPE_TOOLTIP,
                classes=(SAB.DENSE, SAB.NO_UNDERLINE, SAB.BADGE_TYPE, _CSS.TYPE_TOOL),
            ),
        ],
    )


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
_ICON_PROMPT = "\U0001f4ac"  # 💬 speech-balloon — prompts are conversation templates
_ICON_RESOURCE = "\U0001f5c2\ufe0f"  # 🗂️ card-index — fixed-URI documents
_ICON_RESOURCE_TEMPLATE = "\U0001f9ed"  # 🧭 compass — parameterised URIs


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
            icon=_ICON_PROMPT,
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

    Emits a type badge (``resource`` or ``resource-template``), a MIME
    pill if one is set, and optional tag pills.

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
            icon=_ICON_RESOURCE_TEMPLATE,
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
            icon=_ICON_RESOURCE,
            classes=(
                SAB.DENSE,
                SAB.NO_UNDERLINE,
                SAB.BADGE_TYPE,
                _CSS.TYPE_RESOURCE,
            ),
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
