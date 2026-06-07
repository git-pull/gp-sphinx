"""Rendering directives for docutils writer documentation."""

from __future__ import annotations

import inspect
import typing as t

from docutils.parsers.rst import directives
from docutils.writers import Writer
from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_docutils._badges import build_kind_badge_group
from sphinx_autodoc_docutils._components import (
    component_classes,
    import_component,
    render_component_nodes,
    safe_transform_names,
)
from sphinx_autodoc_docutils._directives import _literal_paragraph, _summary
from sphinx_autodoc_docutils.domain import WRITER
from sphinx_ux_autodoc_layout import ApiFactRow

if t.TYPE_CHECKING:
    from docutils import nodes
    from sphinx.util.typing import OptionSpec


def discover_writers(module_name: str) -> list[type[Writer[t.Any]]]:
    """Return public writer classes defined in a module.

    Writers have no Sphinx-side registration call, so discovery is a
    module subclass scan (django-docutils instantiates its writer
    directly inside a publisher).

    Examples
    --------
    >>> writers = discover_writers("docutils.writers.html5_polyglot")
    >>> [cls.__name__ for cls in writers]
    ['Writer']

    >>> discover_writers("sphinx_fonts")
    []
    """
    return component_classes(module_name, Writer)


def discover_writer(path: str) -> type[Writer[t.Any]]:
    """Return one writer class from a fully-qualified dotted path.

    Examples
    --------
    >>> discover_writer("docutils.writers.html5_polyglot.Writer").supported
    ('html5', 'xhtml', 'html')
    """
    return t.cast("type[Writer[t.Any]]", import_component(path))


def resolve_translator_class(cls: type[Writer[t.Any]]) -> type | None:
    """Return the writer's translator class, instantiating defensively.

    Writers commonly assign ``translator_class`` in ``__init__`` rather
    than as a class attribute (django-docutils does), so instantiate
    first and fall back to the class attribute when construction needs
    framework state.

    Examples
    --------
    >>> from docutils.writers import html5_polyglot
    >>> resolve_translator_class(html5_polyglot.Writer).__name__
    'HTMLTranslator'
    """
    translator: object
    try:
        translator = getattr(cls(), "translator_class", None)
    except Exception:  # noqa: BLE001 — degrade to the class attribute on any error
        translator = getattr(cls, "translator_class", None)
    if inspect.isclass(translator):
        return translator
    return None


def _writer_fact_rows(cls: type[Writer[t.Any]]) -> list[ApiFactRow]:
    """Return shared fact rows for one autodocumented writer.

    Examples
    --------
    >>> from docutils.writers import html5_polyglot
    >>> rows = _writer_fact_rows(html5_polyglot.Writer)
    >>> [row.label for row in rows]
    ['Python path', 'Supported formats', 'Translator class', 'Config section', 'Transforms']
    """
    translator = resolve_translator_class(cls)
    translator_path = (
        f"{translator.__module__}.{translator.__name__}"
        if translator is not None
        else "—"
    )
    return [
        ApiFactRow(
            "Python path",
            _literal_paragraph(f"{cls.__module__}.{cls.__name__}"),
        ),
        ApiFactRow(
            "Supported formats",
            _literal_paragraph(", ".join(cls.supported) or "—"),
        ),
        ApiFactRow("Translator class", _literal_paragraph(translator_path)),
        ApiFactRow(
            "Config section",
            _literal_paragraph(cls.config_section or "—"),
        ),
        ApiFactRow(
            "Transforms",
            _literal_paragraph(", ".join(safe_transform_names(cls)) or "—"),
        ),
    ]


def _render_writer(
    directive: SphinxDirective,
    cls: type[Writer[t.Any]],
    *,
    no_index: bool = False,
) -> list[nodes.Node]:
    """Render one writer entry through the shared component pipeline."""
    return render_component_nodes(
        directive,
        objtype=WRITER,
        path=f"{cls.__module__}.{cls.__name__}",
        summary=_summary(cls),
        fact_rows=_writer_fact_rows(cls),
        badge_group=build_kind_badge_group(WRITER),
        no_index=no_index,
    )


class AutoWriter(SphinxDirective):
    """Render documentation for a single writer class."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        cls = discover_writer(self.arguments[0])
        return _render_writer(self, cls, no_index="no-index" in self.options)


class AutoWriters(SphinxDirective):
    """Render documentation for every writer class a module defines."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        no_index = "no-index" in self.options
        results: list[nodes.Node] = []
        for cls in discover_writers(self.arguments[0]):
            results.extend(_render_writer(self, cls, no_index=no_index))
        return results
