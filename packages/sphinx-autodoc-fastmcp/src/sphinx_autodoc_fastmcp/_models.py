"""Data models for FastMCP tool / prompt / resource documentation."""

from __future__ import annotations

import typing as t
from dataclasses import dataclass, field


@dataclass
class ParamInfo:
    """Extracted parameter information for a tool."""

    name: str
    type_str: str
    required: bool
    default: str
    description: str


@dataclass
class ToolInfo:
    """Collected metadata for a single MCP tool."""

    name: str
    title: str
    module_name: str
    area: str
    safety: str
    annotations: dict[str, bool]
    func: t.Callable[..., t.Any]
    docstring: str
    params: list[ParamInfo]
    return_annotation: str


@dataclass
class PromptArgInfo:
    """One ``arguments[]`` entry on an MCP prompt."""

    name: str
    description: str
    required: bool
    type_str: str = ""


@dataclass
class PromptInfo:
    """Collected metadata for a single MCP prompt.

    The underlying function is intentionally not retained — FastMCP
    resources and prompts are frequently defined as closure-local
    functions, which cannot be pickled into Sphinx's environment
    cache.  We extract the docstring eagerly at collect time.
    """

    name: str
    title: str
    description: str
    docstring: str
    tags: tuple[str, ...]
    arguments: list[PromptArgInfo]
    module_name: str = ""


@dataclass
class ResourceInfo:
    """Collected metadata for a single MCP resource (fixed URI)."""

    name: str
    uri: str
    title: str
    description: str
    mime_type: str
    docstring: str
    tags: tuple[str, ...] = ()
    annotations: dict[str, t.Any] = field(default_factory=dict)
    module_name: str = ""


@dataclass
class ResourceTemplateInfo:
    """Collected metadata for a single MCP resource *template* (URI pattern)."""

    name: str
    uri_template: str
    title: str
    description: str
    mime_type: str
    parameters: list[PromptArgInfo]
    docstring: str
    tags: tuple[str, ...] = ()
    annotations: dict[str, t.Any] = field(default_factory=dict)
    module_name: str = ""
