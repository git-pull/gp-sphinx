"""Inline roles for FastMCP tool cross-references."""

from __future__ import annotations

import typing as t

from docutils import nodes


class _tool_ref_placeholder(nodes.General, nodes.Inline, nodes.Element):
    """Placeholder resolved at ``doctree-resolved``."""


def _tool_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: object,
    options: dict[str, object] | None = None,
    content: list[str] | None = None,
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    """Role ``:tool:`name``` → link + badge (resolved later)."""
    target = text.strip().replace("_", "-")
    node = _tool_ref_placeholder(rawtext, reftarget=target, show_badge=True)
    return [node], []


def _toolref_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: object,
    options: dict[str, object] | None = None,
    content: list[str] | None = None,
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    """Role ``:toolref:`name``` → link without badge."""
    target = text.strip().replace("_", "-")
    node = _tool_ref_placeholder(rawtext, reftarget=target, show_badge=False)
    return [node], []


def _make_toolicon_role(
    icon_pos: str,
) -> t.Callable[..., tuple[list[nodes.Node], list[nodes.system_message]]]:
    """Create an icon-only tool reference role callable."""

    def role_fn(
        name: str,
        rawtext: str,
        text: str,
        lineno: int,
        inliner: object,
        options: dict[str, object] | None = None,
        content: list[str] | None = None,
    ) -> tuple[list[nodes.Node], list[nodes.system_message]]:
        target = text.strip().replace("_", "-")
        node = _tool_ref_placeholder(
            rawtext,
            reftarget=target,
            show_badge=False,
            icon_pos=icon_pos,
        )
        return [node], []

    return role_fn


_toolicon_role = _make_toolicon_role("left")
_tooliconl_role = _make_toolicon_role("left")
_tooliconr_role = _make_toolicon_role("right")
_tooliconil_role = _make_toolicon_role("inline-left")
_tooliconir_role = _make_toolicon_role("inline-right")
