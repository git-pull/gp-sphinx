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


class _component_ref_placeholder(nodes.General, nodes.Inline, nodes.Element):
    """Placeholder for prompt/resource cross-refs, resolved at ``doctree-resolved``.

    Unlike tools, resources and prompts carry no bare-slug alias. The
    ``refkind`` attribute selects the canonical-id family that
    :func:`sphinx_autodoc_fastmcp._transforms.resolve_component_refs` looks up:
    ``prompt`` targets the single ``fastmcp-prompt-<slug>`` id, while
    ``resource`` tries ``fastmcp-resource-<slug>`` then
    ``fastmcp-resource-template-<slug>`` so one spelling links either.
    """


def _make_component_ref_role(
    refkind: str,
) -> t.Callable[..., tuple[list[nodes.Node], list[nodes.system_message]]]:
    """Create a resource/prompt cross-reference role callable.

    The role renders an inline code literal linked to the component card; it
    carries no safety badge (only tools have a safety tier).

    Parameters
    ----------
    refkind : str
        Component family the role resolves against — ``"resource"`` or
        ``"prompt"``. Stored on the placeholder so
        :func:`sphinx_autodoc_fastmcp._transforms.resolve_component_refs`
        picks the right canonical-id family.

    Returns
    -------
    collections.abc.Callable
        A docutils role function ``(name, rawtext, text, lineno, inliner,
        options=None, content=None)`` returning ``([placeholder], [])``.

    Examples
    --------
    >>> role = _make_component_ref_role("resource")
    >>> emitted, messages = role("resource", "", "user_record", 0, None)
    >>> emitted[0]["refkind"], emitted[0]["refslug"], emitted[0]["reftext"]
    ('resource', 'user-record', 'user_record')
    >>> messages
    []
    """

    def role_fn(
        name: str,
        rawtext: str,
        text: str,
        lineno: int,
        inliner: object,
        options: dict[str, object] | None = None,
        content: list[str] | None = None,
    ) -> tuple[list[nodes.Node], list[nodes.system_message]]:
        display = text.strip()
        node = _component_ref_placeholder(
            rawtext,
            refkind=refkind,
            refslug=display.replace("_", "-"),
            reftext=display,
        )
        return [node], []

    return role_fn


# ``{resource}`` covers both fixed resources and resource templates (the
# resolver tries each id family in turn); ``{resourceref}`` is the explicit
# plain-reference spelling mirroring ``{toolref}``.
_resource_role = _make_component_ref_role("resource")
_resourceref_role = _make_component_ref_role("resource")
_prompt_role = _make_component_ref_role("prompt")
_promptref_role = _make_component_ref_role("prompt")
