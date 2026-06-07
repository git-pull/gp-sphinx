"""Rendering directives for docutils transform documentation."""

from __future__ import annotations

import inspect
import typing as t
from dataclasses import dataclass

from docutils.parsers.rst import directives
from docutils.transforms import Transform
from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_docutils._badges import build_transform_badge_group
from sphinx_autodoc_docutils._components import (
    component_classes,
    import_component,
    linked_paragraph,
    render_component_nodes,
)
from sphinx_autodoc_docutils._directives import (
    _literal_paragraph,
    _summary,
    replay_setup,
)
from sphinx_autodoc_docutils.domain import TRANSFORM
from sphinx_ux_autodoc_layout import ApiFactRow

if t.TYPE_CHECKING:
    from docutils import nodes
    from sphinx.util.typing import OptionSpec

#: Recorder call names that register a transform with Sphinx.
_TRANSFORM_CALLS: tuple[str, ...] = ("add_transform", "add_post_transform")


@dataclass(frozen=True)
class TransformInfo:
    """Recorded metadata for one documented transform class.

    Examples
    --------
    >>> from docutils.transforms.misc import Transitions
    >>> info = TransformInfo(cls=Transitions, registered_via="add_transform")
    >>> info.qualified_name
    'docutils.transforms.misc.Transitions'
    >>> info.priority
    830
    """

    cls: type[Transform]
    registered_via: str = ""

    @property
    def qualified_name(self) -> str:
        """Return the fully-qualified dotted path for the class.

        Examples
        --------
        >>> from docutils.transforms.misc import CallBack
        >>> TransformInfo(cls=CallBack).qualified_name
        'docutils.transforms.misc.CallBack'
        """
        return f"{self.cls.__module__}.{self.cls.__name__}"

    @property
    def priority(self) -> int | None:
        """Return the transform's ``default_priority`` (None on bases).

        Examples
        --------
        >>> from docutils.transforms.misc import CallBack
        >>> TransformInfo(cls=CallBack).priority
        990
        """
        return self.cls.default_priority


def _transforms_from_calls(
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]],
) -> list[TransformInfo]:
    """Extract transform metadata from recorded ``setup()`` calls.

    Examples
    --------
    >>> from docutils.transforms.misc import CallBack, Transitions
    >>> infos = _transforms_from_calls(
    ...     [
    ...         ("add_transform", (Transitions,), {}),
    ...         ("add_post_transform", (CallBack,), {}),
    ...         ("add_directive", ("noise", object), {}),
    ...     ],
    ... )
    >>> [(info.cls.__name__, info.registered_via) for info in infos]
    [('Transitions', 'add_transform'), ('CallBack', 'add_post_transform')]
    """
    infos: list[TransformInfo] = []
    seen: set[tuple[type[Transform], str]] = set()
    for call_name, args, _kwargs in calls:
        if call_name not in _TRANSFORM_CALLS or len(args) < 1:
            continue
        cls = args[0]
        if not (inspect.isclass(cls) and issubclass(cls, Transform)):
            continue
        key = (cls, call_name)
        if key in seen:
            continue
        seen.add(key)
        infos.append(TransformInfo(cls=cls, registered_via=call_name))
    return infos


def discover_transforms(module_name: str) -> list[TransformInfo]:
    """Return transforms a module registers, or defines as a fallback.

    Replays the module's ``setup()`` against a recorder so transforms
    surface with their real registration phase (``add_transform`` vs
    ``add_post_transform``). Falls back to scanning the module for
    public :class:`~docutils.transforms.Transform` subclasses when no
    ``setup()`` registers any.

    Examples
    --------
    >>> infos = discover_transforms("docutils.transforms.misc")
    >>> sorted(info.cls.__name__ for info in infos)
    ['CallBack', 'ClassAttribute', 'Transitions']
    >>> {info.registered_via for info in infos}
    {''}

    >>> discover_transforms("sphinx_fonts")
    []
    """
    recorder = replay_setup(module_name)
    if recorder is not None:
        infos = _transforms_from_calls(recorder.calls)
        if infos:
            return infos
    return [TransformInfo(cls=cls) for cls in component_classes(module_name, Transform)]


def discover_transform(path: str) -> TransformInfo:
    """Return one transform from a fully-qualified dotted path.

    Examples
    --------
    >>> info = discover_transform("docutils.transforms.misc.Transitions")
    >>> info.cls.__name__
    'Transitions'
    """
    cls = t.cast("type[Transform]", import_component(path))
    for info in discover_transforms(cls.__module__):
        if info.cls is cls:
            return info
    return TransformInfo(cls=cls)


def _transform_fact_rows(info: TransformInfo) -> list[ApiFactRow]:
    """Return shared fact rows for one autodocumented transform.

    Examples
    --------
    >>> from docutils.transforms.misc import Transitions
    >>> rows = _transform_fact_rows(
    ...     TransformInfo(cls=Transitions, registered_via="add_transform"),
    ... )
    >>> [row.label for row in rows]
    ['Python path', 'Default priority', 'Registered via']
    """
    rows = [
        ApiFactRow("Python path", linked_paragraph(info.qualified_name)),
        ApiFactRow(
            "Default priority",
            _literal_paragraph(
                str(info.priority) if info.priority is not None else "—",
            ),
        ),
    ]
    if info.registered_via:
        rows.append(
            ApiFactRow(
                "Registered via",
                # Links to the Sphinx Application API when the sphinx
                # inventory is mapped; degrades to the literal call.
                linked_paragraph(
                    f"sphinx.application.Sphinx.{info.registered_via}",
                    f"app.{info.registered_via}()",
                ),
            ),
        )
    return rows


def _render_transform(
    directive: SphinxDirective,
    info: TransformInfo,
    *,
    no_index: bool = False,
) -> list[nodes.Node]:
    """Render one transform entry through the shared component pipeline."""
    return render_component_nodes(
        directive,
        objtype=TRANSFORM,
        path=info.qualified_name,
        summary=_summary(info.cls),
        fact_rows=_transform_fact_rows(info),
        badge_group=build_transform_badge_group(info.priority),
        no_index=no_index,
    )


class AutoTransform(SphinxDirective):
    """Render documentation for a single transform class."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        info = discover_transform(self.arguments[0])
        return _render_transform(self, info, no_index="no-index" in self.options)


class AutoTransforms(SphinxDirective):
    """Render documentation for every transform a package registers.

    Accepts either an extension package (whose ``setup()`` runs against
    a recorder so each ``app.add_transform(cls)`` /
    ``app.add_post_transform(cls)`` call surfaces with its phase) or a
    transform-defining module (introspected for ``Transform``
    subclasses).
    """

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        no_index = "no-index" in self.options
        results: list[nodes.Node] = []
        for info in discover_transforms(self.arguments[0]):
            results.extend(_render_transform(self, info, no_index=no_index))
        return results
