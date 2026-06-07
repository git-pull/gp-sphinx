"""Rendering directives for docutils translator documentation."""

from __future__ import annotations

import inspect
import typing as t
from dataclasses import dataclass

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_docutils._badges import build_translator_badge_group
from sphinx_autodoc_docutils._components import (
    component_classes,
    import_component,
    render_component_nodes,
)
from sphinx_autodoc_docutils._directives import (
    _literal_paragraph,
    _summary,
    replay_setup,
)
from sphinx_autodoc_docutils.domain import TRANSLATOR
from sphinx_ux_autodoc_layout import ApiFactRow

if t.TYPE_CHECKING:
    from sphinx.util.typing import OptionSpec


@dataclass(frozen=True)
class TranslatorInfo:
    """Recorded metadata for one documented translator class.

    Examples
    --------
    >>> from docutils.writers.html5_polyglot import HTMLTranslator
    >>> info = TranslatorInfo(cls=HTMLTranslator, builder_name="html")
    >>> info.qualified_name
    'docutils.writers.html5_polyglot.HTMLTranslator'
    >>> info.builder_name
    'html'
    """

    cls: type[nodes.NodeVisitor]
    builder_name: str = ""
    override: bool = False

    @property
    def qualified_name(self) -> str:
        """Return the fully-qualified dotted path for the class.

        Examples
        --------
        >>> TranslatorInfo(cls=nodes.SparseNodeVisitor).qualified_name
        'docutils.nodes.SparseNodeVisitor'
        """
        return f"{self.cls.__module__}.{self.cls.__name__}"


def translator_overrides(cls: type[nodes.NodeVisitor]) -> list[str]:
    """Return the visit/depart methods defined on the class itself.

    Uses ``vars()`` rather than ``dir()`` so only the class's own
    overrides surface, not the hundreds of handlers inherited from its
    base translator.

    Examples
    --------
    >>> from docutils.writers.html5_polyglot import HTMLTranslator
    >>> "depart_acronym" in translator_overrides(HTMLTranslator)
    True

    ``SparseNodeVisitor`` generates every handler directly on the
    class, so only the abstract ``NodeVisitor`` base is truly empty:

    >>> translator_overrides(nodes.NodeVisitor)
    []
    """
    return sorted(name for name in vars(cls) if name.startswith(("visit_", "depart_")))


def _translators_from_calls(
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]],
) -> list[TranslatorInfo]:
    """Extract translator metadata from recorded ``set_translator`` calls.

    Examples
    --------
    >>> infos = _translators_from_calls(
    ...     [
    ...         ("set_translator", ("html", nodes.SparseNodeVisitor), {"override": True}),
    ...         ("add_directive", ("noise", object), {}),
    ...     ],
    ... )
    >>> [(info.builder_name, info.override) for info in infos]
    [('html', True)]
    """
    infos: list[TranslatorInfo] = []
    for call_name, args, kwargs in calls:
        if call_name != "set_translator" or len(args) < 2:
            continue
        builder_name, cls = args[0], args[1]
        if not (
            isinstance(builder_name, str)
            and inspect.isclass(cls)
            and issubclass(cls, nodes.NodeVisitor)
        ):
            continue
        override = bool(kwargs.get("override", args[2] if len(args) > 2 else False))
        infos.append(
            TranslatorInfo(cls=cls, builder_name=builder_name, override=override),
        )
    return infos


def discover_translators(module_name: str) -> list[TranslatorInfo]:
    """Return translator classes a module defines or registers.

    Combines a module subclass scan for
    :class:`~docutils.nodes.NodeVisitor` subclasses with the module's
    recorded ``app.set_translator()`` calls, so scanned classes carry
    their builder registration and override flag.

    Examples
    --------
    >>> infos = discover_translators("docutils.writers.html5_polyglot")
    >>> [(info.cls.__name__, info.builder_name) for info in infos]
    [('HTMLTranslator', '')]

    >>> discover_translators("sphinx_fonts")
    []
    """
    recorder = replay_setup(module_name)
    registered = _translators_from_calls(recorder.calls) if recorder is not None else []
    by_cls = {info.cls: info for info in registered}
    infos = [
        by_cls.get(cls, TranslatorInfo(cls=cls))
        for cls in component_classes(module_name, nodes.NodeVisitor)
    ]
    scanned = {info.cls for info in infos}
    infos.extend(info for info in registered if info.cls not in scanned)
    return infos


def discover_translator(path: str) -> TranslatorInfo:
    """Return one translator from a fully-qualified dotted path.

    Examples
    --------
    >>> info = discover_translator("docutils.writers.html5_polyglot.HTMLTranslator")
    >>> info.cls.__name__
    'HTMLTranslator'
    """
    cls = t.cast("type[nodes.NodeVisitor]", import_component(path))
    for info in discover_translators(cls.__module__):
        if info.cls is cls:
            return info
    return TranslatorInfo(cls=cls)


def _translator_fact_rows(info: TranslatorInfo) -> list[ApiFactRow]:
    """Return shared fact rows for one autodocumented translator.

    Examples
    --------
    >>> from docutils.writers.html5_polyglot import HTMLTranslator
    >>> rows = _translator_fact_rows(TranslatorInfo(cls=HTMLTranslator))
    >>> [row.label for row in rows]
    ['Python path', 'Base class', 'Overrides']
    """
    overrides = ", ".join(translator_overrides(info.cls)) or "—"
    rows = [
        ApiFactRow("Python path", _literal_paragraph(info.qualified_name)),
        ApiFactRow(
            "Base class",
            _literal_paragraph(info.cls.__bases__[0].__name__),
        ),
        ApiFactRow("Overrides", _literal_paragraph(overrides)),
    ]
    if info.builder_name:
        rows.append(
            ApiFactRow(
                "Registered for builder",
                _literal_paragraph(info.builder_name),
            ),
        )
    return rows


def _render_translator(
    directive: SphinxDirective,
    info: TranslatorInfo,
    *,
    no_index: bool = False,
) -> list[nodes.Node]:
    """Render one translator entry through the shared component pipeline."""
    return render_component_nodes(
        directive,
        objtype=TRANSLATOR,
        path=info.qualified_name,
        summary=_summary(info.cls),
        fact_rows=_translator_fact_rows(info),
        badge_group=build_translator_badge_group(override=info.override),
        no_index=no_index,
    )


class AutoTranslator(SphinxDirective):
    """Render documentation for a single translator class."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        info = discover_translator(self.arguments[0])
        return _render_translator(self, info, no_index="no-index" in self.options)


class AutoTranslators(SphinxDirective):
    """Render documentation for every translator a module defines or registers."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        no_index = "no-index" in self.options
        results: list[nodes.Node] = []
        for info in discover_translators(self.arguments[0]):
            results.extend(_render_translator(self, info, no_index=no_index))
        return results
