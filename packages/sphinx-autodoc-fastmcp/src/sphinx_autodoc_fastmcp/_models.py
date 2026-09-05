"""Data models for FastMCP tool / prompt / resource documentation."""

from __future__ import annotations

import logging
import typing as t
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

#: Sources an axis can read a tool's term from. ``tags`` matches declared
#: terms against ``tool.tags``; ``annotations`` derives one from the MCP
#: hints; ``meta:<key>`` reads ``tool.meta[<key>]``.
AxisSource = str


@dataclass(frozen=True)
class Term:
    """One value an axis can take, and how it renders.

    Attributes
    ----------
    term : str
        Value to match, and the badge label unless ``label`` overrides it.
    label : str
        Badge text. Defaults to ``term``.
    tooltip : str
        Hover text. Falls back to ``"<axis>: <term>"``.
    icon : str
        Emoji rendered before the label. Optional.
    tone : str
        Colour name. Any name works: the badge gets ``--tone-<tone>`` and
        the stylesheet decides what that means.
    style : str
        ``full``, ``icon-only`` or ``inline-icon``.
    fill : str
        ``filled`` or ``outline``.
    classes : tuple of str
        Extra CSS classes, for styling this term alone.
    """

    term: str
    label: str = ""
    tooltip: str = ""
    icon: str = ""
    tone: str = "slate"
    style: str = "full"
    fill: str = "filled"
    classes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Axis:
    """One independent way of classifying a tool.

    A tool takes at most one term per axis, so two axes render two badges.

    Attributes
    ----------
    name : str
        Axis identifier, used in the CSS class and the default tooltip.
    source : str
        Where the term comes from. See :data:`AxisSource`.
    terms : tuple of Term
        Vocabulary in precedence order, highest first.
    """

    name: str
    source: AxisSource = "tags"
    terms: tuple[Term, ...] = ()

    def term(self, value: str) -> Term | None:
        """Return the declared term named ``value``, or ``None``."""
        return next((t_ for t_ in self.terms if t_.term == value), None)


#: Per the MCP spec ``destructiveHint`` describes a tool only once
#: ``readOnlyHint`` is false, so the terms are ordered to read it second.
ANNOTATION_AXIS = Axis(
    name="risk",
    source="annotations",
    terms=(
        Term(
            "destructive",
            tooltip="Destructive \N{EM DASH} may remove data",
            icon="\N{BOMB}",
            tone="red",
        ),
        Term(
            "mutating",
            tooltip="Mutating \N{EM DASH} changes state additively",
            icon="\N{PENCIL}\N{VARIATION SELECTOR-16}",
            tone="amber",
        ),
        Term(
            "readonly",
            tooltip="Read-only \N{EM DASH} does not modify its environment",
            icon="\N{LEFT-POINTING MAGNIFYING GLASS}",
            tone="green",
        ),
    ),
)

DEFAULT_AXES: tuple[Axis, ...] = (ANNOTATION_AXIS,)


#: Component families whose canonical ids are ``fastmcp-<kind>-<slug>``
#: (see ``_directives._component_ids``). An axis sharing one of these names
#: would emit ``fastmcp-<kind>-<term>`` summary anchors into the same id
#: namespace, and cross-reference roles resolve canonical ids first.
COMPONENT_KINDS: tuple[str, ...] = ("tool", "prompt", "resource", "resource-template")


def _coerce_term(value: t.Any) -> Term | None:
    """Return a :class:`Term` from a string or mapping, or ``None``."""
    if isinstance(value, Term):
        return value
    if isinstance(value, str):
        return Term(value)
    term = value.get("term", value.get("tag"))
    if not term:
        logger.warning(
            "sphinx_autodoc_fastmcp: toolset term %r has no 'term'; skipping it",
            value,
        )
        return None
    return Term(
        term,
        label=value.get("label", ""),
        tooltip=value.get("tooltip", ""),
        icon=value.get("icon", ""),
        tone=value.get("tone", "slate"),
        style=value.get("style", "full"),
        fill=value.get("fill", "filled"),
        classes=tuple(value.get("classes", ())),
    )


def _is_reserved_axis_name(name: str) -> bool:
    """Return whether *name* collides with a component id namespace.

    An axis named after a component kind emits ``fastmcp-<kind>-<term>``
    anchors, which share the namespace that ``{tool}``, ``{resource}`` and
    ``{prompt}`` resolve against. Warns once per offending axis and reports
    it as reserved so the caller can drop it.

    Parameters
    ----------
    name : str
        Declared axis name.

    Returns
    -------
    bool
        ``True`` when the axis must be dropped.

    Examples
    --------
    >>> _is_reserved_axis_name("capability")
    False
    >>> _is_reserved_axis_name("tool")
    True
    """
    if name not in COMPONENT_KINDS:
        return False
    logger.warning(
        "sphinx_autodoc_fastmcp: fastmcp_axes declares an axis named %r, which "
        "generates 'fastmcp-%s-<term>' summary anchors that collide with the "
        "canonical 'fastmcp-%s-<slug>' ids of %s components; cross-reference "
        "roles resolve the canonical id first, so the axis is skipped — rename "
        "it (for example %r) to keep its badges",
        name,
        name,
        name,
        name,
        f"{name}-kind",
    )
    return True


def coerce_axes(value: t.Any) -> tuple[Axis, ...]:
    """Return the axis list a ``fastmcp_axes`` value describes.

    Accepts what a ``conf.py`` can express: a sequence of :class:`Axis` or
    of mappings with ``name``, optional ``source``, and ``terms``. An empty
    value declares no axes, and tools then carry no badges.

    Parameters
    ----------
    value : object
        Raw configuration value.

    Returns
    -------
    tuple of Axis
        Axes in declaration order; badges render in that order.

    Examples
    --------
    >>> axes = coerce_axes(({"name": "topic", "terms": ("search", "admin")},))
    >>> axes[0].name, [t.term for t in axes[0].terms]
    ('topic', ['search', 'admin'])
    """
    if not value:
        return ()
    axes: list[Axis] = []
    for entry in value:
        if isinstance(entry, Axis):
            if _is_reserved_axis_name(entry.name):
                continue
            axes.append(entry)
            continue
        name = entry.get("name")
        if not name:
            logger.warning(
                "sphinx_autodoc_fastmcp: fastmcp_axes entry %r has no 'name'; "
                "skipping it",
                entry,
            )
            continue
        if _is_reserved_axis_name(name):
            continue
        terms = tuple(
            t_ for t_ in (_coerce_term(v) for v in entry.get("terms", ())) if t_
        )
        axes.append(Axis(name, entry.get("source", "tags"), terms))
    return tuple(axes)


def term_from_annotations(hints: dict[str, bool]) -> str:
    """Return the risk term MCP's hints imply, or ``""``.

    Follows the spec: ``destructiveHint`` and ``idempotentHint`` describe a
    tool only once ``readOnlyHint`` is false, and an unset hint says
    nothing rather than defaulting.

    Examples
    --------
    >>> term_from_annotations({"readOnlyHint": True})
    'readonly'
    >>> term_from_annotations({"readOnlyHint": False, "destructiveHint": True})
    'destructive'
    >>> term_from_annotations({"readOnlyHint": False})
    'mutating'
    >>> term_from_annotations({})
    ''
    """
    read_only = hints.get("readOnlyHint")
    if read_only is True:
        return "readonly"
    if read_only is False:
        return "destructive" if hints.get("destructiveHint") else "mutating"
    return ""


def resolve_axes(
    axes: t.Sequence[Axis],
    *,
    tags: t.Iterable[str] = (),
    annotations: dict[str, bool] | None = None,
    meta: dict[str, t.Any] | None = None,
) -> dict[str, str]:
    """Return the term each axis places a tool in.

    An axis with no match is left out rather than given a fallback: naming
    one would report a tool as something nobody classified it as.

    Parameters
    ----------
    axes : sequence of Axis
        Declared axes.
    tags : iterable of str
        The tool's tags.
    annotations : dict of str to bool, optional
        MCP hints the tool sets.
    meta : dict, optional
        The tool's ``meta`` mapping.

    Returns
    -------
    dict
        Axis name to term, for axes that matched.

    Examples
    --------
    >>> axes = coerce_axes(({"name": "topic", "terms": ("admin", "search")},))
    >>> resolve_axes(axes, tags={"search"})
    {'topic': 'search'}
    >>> resolve_axes(axes, tags={"other"})
    {}
    """
    present = set(tags)
    hints = annotations or {}
    data = meta or {}
    resolved: dict[str, str] = {}
    for axis in axes:
        if axis.source == "annotations":
            value = term_from_annotations(hints)
        elif axis.source.startswith("meta:"):
            raw = data.get(axis.source[len("meta:") :])
            value = str(raw) if raw is not None else ""
        else:
            value = next((t_.term for t_ in axis.terms if t_.term in present), "")
        if value:
            resolved[axis.name] = value
    return resolved


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
    axes : dict[str, str]
        Term this tool takes on each declared axis, for axes that matched.
    annotations : dict[str, bool]
        MCP hint flags such as ``readOnlyHint`` and ``destructiveHint``,
        holding only the hints the tool actually sets.
    meta : dict[str, t.Any]
        The tool's ``meta`` mapping, which axes can read terms from.
    func : t.Callable[..., t.Any] | None
        The undecorated tool function. Dropped when Sphinx pickles its
        environment between builds — a tool registered inside a factory is
        a closure, and a closure cannot be pickled — so it is ``None`` on
        any incremental rebuild. Everything rendered is captured at
        collection time in ``params``, ``return_annotation`` and
        ``docstring``; nothing reads this field.
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
    axes: dict[str, str]
    annotations: dict[str, bool]
    meta: dict[str, t.Any]
    func: t.Callable[..., t.Any] | None
    docstring: str
    params: list[ParamInfo]
    return_annotation: str

    def __getstate__(self) -> dict[str, t.Any]:
        """Drop ``func`` so Sphinx can pickle its environment.

        A tool registered inside a ``register(mcp)`` factory is a local
        function, and pickling one raises. Nothing reads the field, so
        dropping it costs nothing and keeps incremental builds working.
        """
        return {**self.__dict__, "func": None}


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
