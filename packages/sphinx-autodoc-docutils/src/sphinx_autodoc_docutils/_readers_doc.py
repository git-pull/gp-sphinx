"""Rendering directives for docutils reader documentation."""

from __future__ import annotations

import typing as t

from docutils.parsers.rst import directives
from docutils.readers import Reader
from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_docutils._badges import build_kind_badge_group
from sphinx_autodoc_docutils._components import (
    component_classes,
    import_component,
    linked_paragraph,
    render_component_nodes,
    transform_chip_nodes,
)
from sphinx_autodoc_docutils._directives import _literal_paragraph, _summary
from sphinx_autodoc_docutils.domain import READER
from sphinx_ux_autodoc_layout import ApiFactRow, build_chip_paragraph

if t.TYPE_CHECKING:
    from docutils import nodes
    from sphinx.util.typing import OptionSpec


def discover_readers(module_name: str) -> list[type[Reader[t.Any]]]:
    """Return public reader classes defined in a module.

    Readers have no Sphinx-side registration call, so discovery is a
    module subclass scan (django-docutils, for example, instantiates
    its reader directly inside a publisher).

    Examples
    --------
    >>> readers = discover_readers("docutils.readers.standalone")
    >>> [cls.__name__ for cls in readers]
    ['Reader']

    >>> discover_readers("sphinx_fonts")
    []
    """
    return component_classes(module_name, Reader)


def discover_reader(path: str) -> type[Reader[t.Any]]:
    """Return one reader class from a fully-qualified dotted path.

    Examples
    --------
    >>> discover_reader("docutils.readers.standalone.Reader").supported
    ('standalone',)
    """
    return t.cast("type[Reader[t.Any]]", import_component(path))


def _reader_fact_rows(cls: type[Reader[t.Any]]) -> list[ApiFactRow]:
    """Return shared fact rows for one autodocumented reader.

    Examples
    --------
    >>> from docutils.readers.standalone import Reader
    >>> rows = _reader_fact_rows(Reader)
    >>> [row.label for row in rows]
    ['Python path', 'Supported formats', 'Config section', 'Transforms']
    """
    return [
        ApiFactRow(
            "Python path",
            linked_paragraph(f"{cls.__module__}.{cls.__name__}"),
        ),
        ApiFactRow("Supported formats", build_chip_paragraph(list(cls.supported))),
        ApiFactRow(
            "Config section",
            _literal_paragraph(cls.config_section or "—"),
        ),
        ApiFactRow("Transforms", build_chip_paragraph(transform_chip_nodes(cls))),
    ]


def _render_reader(
    directive: SphinxDirective,
    cls: type[Reader[t.Any]],
    *,
    no_index: bool = False,
) -> list[nodes.Node]:
    """Render one reader entry through the shared component pipeline."""
    return render_component_nodes(
        directive,
        objtype=READER,
        path=f"{cls.__module__}.{cls.__name__}",
        summary=_summary(cls),
        fact_rows=_reader_fact_rows(cls),
        badge_group=build_kind_badge_group(READER),
        no_index=no_index,
    )


class AutoReader(SphinxDirective):
    """Render documentation for a single reader class."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        cls = discover_reader(self.arguments[0])
        return _render_reader(self, cls, no_index="no-index" in self.options)


class AutoReaders(SphinxDirective):
    """Render documentation for every reader class a module defines."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        no_index = "no-index" in self.options
        results: list[nodes.Node] = []
        for cls in discover_readers(self.arguments[0]):
            results.extend(_render_reader(self, cls, no_index=no_index))
        return results
