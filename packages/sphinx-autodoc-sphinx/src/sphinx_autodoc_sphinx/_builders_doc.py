"""Rendering directives for Sphinx builder documentation."""

from __future__ import annotations

import inspect
import typing as t
from dataclasses import dataclass

from docutils.parsers.rst import directives
from sphinx.builders import Builder
from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_sphinx._badges import build_builder_badge_group
from sphinx_autodoc_sphinx._components import (
    component_classes,
    component_summary,
    import_component,
    render_component_nodes,
    replay_setup,
)
from sphinx_autodoc_sphinx._directives import _literal_paragraph
from sphinx_autodoc_sphinx.domain import BUILDER
from sphinx_ux_autodoc_layout import ApiFactRow

if t.TYPE_CHECKING:
    from docutils import nodes
    from sphinx.util.typing import OptionSpec


@dataclass(frozen=True)
class BuilderInfo:
    """Recorded metadata for one documented builder class.

    Examples
    --------
    >>> from sphinx.builders.dummy import DummyBuilder
    >>> info = BuilderInfo(cls=DummyBuilder, registered=True)
    >>> info.qualified_name
    'sphinx.builders.dummy.DummyBuilder'
    >>> info.builder_name
    'dummy'
    """

    cls: type[Builder]
    registered: bool = False

    @property
    def qualified_name(self) -> str:
        """Return the fully-qualified dotted path for the class.

        Examples
        --------
        >>> from sphinx.builders.dummy import DummyBuilder
        >>> BuilderInfo(cls=DummyBuilder).qualified_name
        'sphinx.builders.dummy.DummyBuilder'
        """
        return f"{self.cls.__module__}.{self.cls.__name__}"

    @property
    def builder_name(self) -> str:
        """Return the builder's CLI name (``-b`` value).

        Examples
        --------
        >>> from sphinx.builders.dummy import DummyBuilder
        >>> BuilderInfo(cls=DummyBuilder).builder_name
        'dummy'
        """
        return str(self.cls.name)


def _builders_from_calls(
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]],
) -> list[BuilderInfo]:
    """Extract builder metadata from recorded ``add_builder`` calls.

    Examples
    --------
    >>> from sphinx.builders.dummy import DummyBuilder
    >>> infos = _builders_from_calls(
    ...     [
    ...         ("add_builder", (DummyBuilder,), {}),
    ...         ("add_directive", ("noise", object), {}),
    ...     ],
    ... )
    >>> [(info.cls.__name__, info.registered) for info in infos]
    [('DummyBuilder', True)]
    """
    infos: list[BuilderInfo] = []
    seen: set[type[Builder]] = set()
    for call_name, args, _kwargs in calls:
        if call_name != "add_builder" or len(args) < 1:
            continue
        cls = args[0]
        if not (inspect.isclass(cls) and issubclass(cls, Builder)):
            continue
        if cls in seen:
            continue
        seen.add(cls)
        infos.append(BuilderInfo(cls=cls, registered=True))
    return infos


def discover_builders(module_name: str) -> list[BuilderInfo]:
    """Return builders a module registers, or defines as a fallback.

    Replays the module's ``setup()`` against a recorder so builders
    surface with their ``app.add_builder()`` registration; falls back
    to scanning the module for public
    :class:`~sphinx.builders.Builder` subclasses.

    Examples
    --------
    >>> infos = discover_builders("sphinx.builders.dummy")
    >>> [(info.cls.__name__, info.registered) for info in infos]
    [('DummyBuilder', True)]

    >>> discover_builders("sphinx_fonts")
    []
    """
    recorder = replay_setup(module_name)
    if recorder is not None:
        infos = _builders_from_calls(recorder.calls)
        if infos:
            return infos
    return [BuilderInfo(cls=cls) for cls in component_classes(module_name, Builder)]


def discover_builder(path: str) -> BuilderInfo:
    """Return one builder from a fully-qualified dotted path.

    Examples
    --------
    >>> info = discover_builder("sphinx.builders.dummy.DummyBuilder")
    >>> info.builder_name
    'dummy'
    """
    cls = t.cast("type[Builder]", import_component(path))
    for info in discover_builders(cls.__module__):
        if info.cls is cls:
            return info
    return BuilderInfo(cls=cls)


def _builder_fact_rows(info: BuilderInfo) -> list[ApiFactRow]:
    """Return shared fact rows for one autodocumented builder.

    Examples
    --------
    >>> from sphinx.builders.dummy import DummyBuilder
    >>> rows = _builder_fact_rows(BuilderInfo(cls=DummyBuilder))
    >>> [row.label for row in rows]  # doctest: +NORMALIZE_WHITESPACE
    ['Python path', 'Builder name', 'Output format',
     'Supported image types', 'Default translator', 'Parallel-safe',
     'Epilog']
    """
    cls = info.cls
    image_types = ", ".join(cls.supported_image_types) or "—"
    # default_translator_class only exists on translator-driven
    # builders (StandaloneHTMLBuilder and friends), not the base.
    translator = getattr(cls, "default_translator_class", None)
    translator_path = (
        f"{translator.__module__}.{translator.__name__}"
        if inspect.isclass(translator)
        else "—"
    )
    return [
        ApiFactRow("Python path", _literal_paragraph(info.qualified_name)),
        ApiFactRow("Builder name", _literal_paragraph(info.builder_name or "—")),
        ApiFactRow("Output format", _literal_paragraph(str(cls.format) or "—")),
        ApiFactRow("Supported image types", _literal_paragraph(image_types)),
        ApiFactRow("Default translator", _literal_paragraph(translator_path)),
        ApiFactRow("Parallel-safe", _literal_paragraph(str(cls.allow_parallel))),
        ApiFactRow("Epilog", _literal_paragraph(str(cls.epilog) or "—")),
    ]


def _render_builder(
    directive: SphinxDirective,
    info: BuilderInfo,
    *,
    no_index: bool = False,
) -> list[nodes.Node]:
    """Render one builder entry through the shared component pipeline."""
    return render_component_nodes(
        directive,
        objtype=BUILDER,
        path=info.qualified_name,
        summary=component_summary(info.cls),
        fact_rows=_builder_fact_rows(info),
        badge_group=build_builder_badge_group(str(info.cls.format)),
        no_index=no_index,
    )


class AutoBuilder(SphinxDirective):
    """Render documentation for a single builder class."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        info = discover_builder(self.arguments[0])
        return _render_builder(self, info, no_index="no-index" in self.options)


class AutoBuilders(SphinxDirective):
    """Render documentation for every builder a package registers.

    Accepts either an extension package (whose ``setup()`` runs against
    a recorder so each ``app.add_builder(cls)`` call surfaces) or a
    builder-defining module (introspected for ``Builder`` subclasses).
    """

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        no_index = "no-index" in self.options
        results: list[nodes.Node] = []
        for info in discover_builders(self.arguments[0]):
            results.extend(_render_builder(self, info, no_index=no_index))
        return results
