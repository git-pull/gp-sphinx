"""Data models for FastMCP tool / prompt / resource documentation."""

from __future__ import annotations

import typing as t
from dataclasses import dataclass, field


@dataclass
class ParamInfo:
    """Extracted parameter information for a tool.

    Attributes
    ----------
    name : str
        Parameter name as it appears in the tool's signature.
    type_str : str
        Rendered annotation text, with ``None`` stripped from the union of
        an optional parameter.
    required : bool
        Whether the signature leaves the parameter without a default.
    default : str
        Rendered default value. Empty for a required parameter.
    description : str
        Text pulled from the function's NumPy ``Parameters`` section. Empty
        when the docstring does not cover the parameter.
    """

    name: str
    type_str: str
    required: bool
    default: str
    description: str


@dataclass
class ToolInfo:
    """Collected metadata for a single MCP tool.

    Attributes
    ----------
    name : str
        Tool name clients call, defaulting to the function name.
    title : str
        Human-facing label, defaulting to the name in title case.
    module_name : str
        Dotted module the tool function was collected from.
    area : str
        Grouping key for the tool, taken from ``fastmcp_area_map`` or
        derived from the module name.
    safety : str
        Risk tier read from the tool's tags — ``"readonly"``,
        ``"mutating"``, or ``"destructive"``.
    annotations : dict[str, bool]
        MCP hint flags such as ``readOnlyHint`` and ``destructiveHint``,
        holding only the hints the tool actually sets.
    func : t.Callable[..., t.Any]
        The undecorated tool function, kept so the renderer can re-inspect
        its signature.
    docstring : str
        Raw ``__doc__`` of the tool function. Empty when it has none.
    params : list[ParamInfo]
        Signature parameters in declaration order.
    return_annotation : str
        Rendered return annotation text.
    """

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
    """One ``arguments[]`` entry on an MCP prompt.

    Also used for the URI placeholders of a resource template.

    Attributes
    ----------
    name : str
        Argument name, matching the prompt signature or the URI
        placeholder.
    description : str
        Prose for the argument, with the trailing JSON-schema note
        stripped. Empty when the component supplies none.
    required : bool
        Whether the caller must supply the argument.
    type_str : str
        Rendered annotation text, filled in from the function signature or
        the template's JSON schema. Empty when neither declares a type.
    """

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

    Attributes
    ----------
    name : str
        Prompt name clients request.
    title : str
        Human-facing label, falling back to the name.
    description : str
        First paragraph of the prompt's registered description. Empty when
        the prompt declares none.
    docstring : str
        Raw ``__doc__`` of the prompt function, captured at collect time.
    tags : tuple[str, ...]
        Prompt tags, sorted. Empty when the prompt carries none.
    arguments : list[PromptArgInfo]
        Prompt arguments in registration order.
    module_name : str
        Dotted module the prompt function was defined in. Empty when the
        function could not be reached through the component.
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
    """Collected metadata for a single MCP resource (fixed URI).

    Attributes
    ----------
    name : str
        Resource name registered with the server.
    uri : str
        Fixed URI clients read the resource at.
    title : str
        Human-facing label, falling back to the name.
    description : str
        First paragraph of the resource's registered description. Empty
        when the resource declares none.
    docstring : str
        Raw ``__doc__`` of the resource function, captured at collect time.
    mime_type : str
        Declared content type. Empty when the resource leaves it unset.
    tags : tuple[str, ...]
        Resource tags, sorted. Empty when the resource carries none.
    annotations : dict[str, t.Any]
        MCP resource annotations — ``audience``, ``priority``, and
        ``lastModified`` — holding only those the resource sets.
    module_name : str
        Dotted module the resource function was defined in. Empty when the
        function could not be reached through the component.
    """

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
    """Collected metadata for a single MCP resource *template* (URI pattern).

    Attributes
    ----------
    name : str
        Template name registered with the server.
    uri_template : str
        URI pattern with placeholders, which clients fill in to read a
        concrete resource.
    title : str
        Human-facing label, falling back to the name.
    description : str
        First paragraph of the template's registered description. Empty
        when the template declares none.
    mime_type : str
        Declared content type. Empty when the template leaves it unset.
    parameters : list[PromptArgInfo]
        URI placeholders flattened from the template's JSON schema.
    docstring : str
        Raw ``__doc__`` of the template function, captured at collect time.
    tags : tuple[str, ...]
        Template tags, sorted. Empty when the template carries none.
    annotations : dict[str, t.Any]
        MCP resource annotations — ``audience``, ``priority``, and
        ``lastModified`` — holding only those the template sets.
    module_name : str
        Dotted module the template function was defined in. Empty when the
        function could not be reached through the component.
    """

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
