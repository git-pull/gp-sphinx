"""Data models for FastMCP tool / prompt / resource documentation."""

from __future__ import annotations

import logging
import typing as t
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

#: Tones the stylesheet defines a rule for. A tone outside this set would
#: render an uncoloured badge, so an unknown one falls back to ``slate``.
TONES: frozenset[str] = frozenset({"green", "blue", "amber", "red", "slate"})


@dataclass(frozen=True)
class Toolset:
    """One entry in the vocabulary a project tags its tools with.

    Attributes
    ----------
    tag : str
        Tag to look for in a tool's ``tags`` set.
    tooltip : str
        Hover text for the badge. Falls back to ``"Toolset: <tag>"``.
    icon : str
        Emoji rendered before the label. Optional.
    tone : str
        Badge colour: ``green``, ``blue``, ``amber``, ``red`` or
        ``slate``. Defaults to ``slate``, which is visible and claims
        nothing — this extension cannot know which of a project's
        toolsets deserves which colour.
    """

    tag: str
    tooltip: str = ""
    icon: str = ""
    tone: str = "slate"


#: No vocabulary is assumed. This extension renders documentation for
#: projects whose tags it does not choose, so shipping a default would
#: badge one project's tools with another's words. A project declares
#: ``fastmcp_toolsets``; until it does, tools render without a toolset
#: badge.
DEFAULT_TOOLSETS: tuple[Toolset, ...] = ()


def coerce_toolsets(value: t.Any) -> tuple[Toolset, ...]:
    """Return a toolset vocabulary from a ``fastmcp_toolsets`` value.

    Accepts what a ``conf.py`` can express: a sequence of mappings, of
    :class:`Toolset`, or of bare tag strings. An empty value declares no
    vocabulary, and tools then carry no toolset badge.

    A mapping with no ``"tag"`` is skipped and a tone outside :data:`TONES`
    falls back to ``slate``, each with a warning, so one typo in ``conf.py``
    costs a badge rather than the build.

    Parameters
    ----------
    value : object
        Raw configuration value.

    Returns
    -------
    tuple of Toolset
        Vocabulary in precedence order, highest first.

    Examples
    --------
    >>> coerce_toolsets(())
    ()
    >>> [entry.tag for entry in coerce_toolsets(("execute", "inspect"))]
    ['execute', 'inspect']
    """
    if not value:
        return DEFAULT_TOOLSETS
    toolsets: list[Toolset] = []
    for entry in value:
        if isinstance(entry, Toolset):
            toolsets.append(entry)
        elif isinstance(entry, str):
            toolsets.append(Toolset(entry))
        elif "tag" not in entry:
            logger.warning(
                "sphinx_autodoc_fastmcp: fastmcp_toolsets entry %r has no "
                "'tag'; skipping it",
                entry,
            )
        else:
            tone = entry.get("tone", "slate")
            if tone not in TONES:
                logger.warning(
                    "sphinx_autodoc_fastmcp: unknown tone %r for toolset %r; "
                    "using 'slate'. Known tones: %s",
                    tone,
                    entry["tag"],
                    ", ".join(sorted(TONES)),
                )
                tone = "slate"
            toolsets.append(
                Toolset(
                    entry["tag"],
                    entry.get("tooltip", ""),
                    entry.get("icon", ""),
                    tone,
                )
            )
    return tuple(toolsets)


def resolve_toolset(
    tags: t.Iterable[str],
    toolsets: t.Sequence[Toolset] = DEFAULT_TOOLSETS,
) -> str:
    """Return the toolset a tool's tags place it in, highest precedence first.

    Returns the empty string when no tag matches. Naming a fallback here
    would report a tool as belonging to a toolset nobody assigned it to,
    which is the one answer a badge must never give.

    Parameters
    ----------
    tags : iterable of str
        The tool's tags.
    toolsets : sequence of Toolset
        Vocabulary in precedence order.

    Returns
    -------
    str
        Matching tag, or ``""`` when the tool carries none of them.

    Examples
    --------
    >>> from sphinx_autodoc_fastmcp._models import coerce_toolsets
    >>> toolsets = coerce_toolsets(("execute", "inspect"))
    >>> resolve_toolset({"execute"}, toolsets)
    'execute'
    >>> resolve_toolset({"unknown"}, toolsets)
    ''
    """
    present = set(tags)
    for entry in toolsets:
        if entry.tag in present:
            return entry.tag
    return ""


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
    toolset : str
        Toolset read from the tool's tags — ``"readonly"``,
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
    toolset: str
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
