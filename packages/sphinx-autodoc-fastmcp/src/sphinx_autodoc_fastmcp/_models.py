"""Data models for FastMCP tool documentation."""

from __future__ import annotations

import typing as t
from dataclasses import dataclass


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
class ResourceInfo:
    """Placeholder for future FastMCP resource documentation."""

    name: str
    uri_template: str = ""
    module_name: str = ""
