"""Rendering directives for docutils parser documentation."""

from __future__ import annotations

import inspect
import typing as t
from dataclasses import dataclass

from docutils.parsers import Parser
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_docutils._badges import build_kind_badge_group
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
from sphinx_autodoc_docutils.domain import PARSER
from sphinx_ux_autodoc_layout import ApiFactRow, build_chip_paragraph

if t.TYPE_CHECKING:
    from docutils import nodes
    from sphinx.util.typing import OptionSpec


@dataclass(frozen=True)
class ParserInfo:
    """Recorded metadata for one documented parser class.

    Examples
    --------
    >>> from docutils.parsers.rst import Parser
    >>> info = ParserInfo(cls=Parser, registered_via="add_source_parser")
    >>> info.qualified_name
    'docutils.parsers.rst.Parser'
    >>> info.aliases[0]
    'rst'
    """

    cls: type[Parser]
    registered_via: str = ""

    @property
    def qualified_name(self) -> str:
        """Return the fully-qualified dotted path for the class.

        Examples
        --------
        >>> from docutils.parsers.rst import Parser
        >>> ParserInfo(cls=Parser).qualified_name
        'docutils.parsers.rst.Parser'
        """
        return f"{self.cls.__module__}.{self.cls.__name__}"

    @property
    def aliases(self) -> tuple[str, ...]:
        """Return the parser's ``supported`` alias tuple.

        Examples
        --------
        >>> from docutils.parsers.rst import Parser
        >>> "restructuredtext" in ParserInfo(cls=Parser).aliases
        True
        """
        return tuple(self.cls.supported)


def _source_parsers_from_calls(
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]],
) -> list[type[Parser]]:
    """Extract parser classes from recorded ``add_source_parser`` calls.

    Examples
    --------
    >>> from docutils.parsers.rst import Parser
    >>> _source_parsers_from_calls(
    ...     [
    ...         ("add_source_parser", (Parser,), {}),
    ...         ("add_directive", ("noise", object), {}),
    ...     ],
    ... )
    [<class 'docutils.parsers.rst.Parser'>]
    """
    classes: list[type[Parser]] = []
    for call_name, args, _kwargs in calls:
        if call_name != "add_source_parser" or len(args) < 1:
            continue
        cls = args[0]
        if inspect.isclass(cls) and issubclass(cls, Parser) and cls not in classes:
            classes.append(cls)
    return classes


def discover_parsers(module_name: str) -> list[ParserInfo]:
    """Return parsers a module defines or registers as source parsers.

    Combines a module subclass scan with the module's recorded
    ``app.add_source_parser()`` calls, so scanned classes carry their
    Sphinx registration state and parsers registered from elsewhere
    still surface.

    Examples
    --------
    >>> infos = discover_parsers("docutils.parsers.rst")
    >>> [(info.cls.__name__, info.registered_via) for info in infos]
    [('Parser', '')]

    >>> discover_parsers("sphinx_fonts")
    []
    """
    recorder = replay_setup(module_name)
    registered = (
        _source_parsers_from_calls(recorder.calls) if recorder is not None else []
    )
    infos = [
        ParserInfo(
            cls=cls,
            registered_via="add_source_parser" if cls in registered else "",
        )
        for cls in component_classes(module_name, Parser)
    ]
    scanned = {info.cls for info in infos}
    infos.extend(
        ParserInfo(cls=cls, registered_via="add_source_parser")
        for cls in registered
        if cls not in scanned
    )
    return infos


def discover_parser(path: str) -> ParserInfo:
    """Return one parser from a fully-qualified dotted path.

    Examples
    --------
    >>> info = discover_parser("docutils.parsers.rst.Parser")
    >>> info.cls.__name__
    'Parser'
    """
    cls = t.cast("type[Parser]", import_component(path))
    for info in discover_parsers(cls.__module__):
        if info.cls is cls:
            return info
    return ParserInfo(cls=cls)


def _parser_fact_rows(info: ParserInfo) -> list[ApiFactRow]:
    """Return shared fact rows for one autodocumented parser.

    Examples
    --------
    >>> from docutils.parsers.rst import Parser
    >>> rows = _parser_fact_rows(ParserInfo(cls=Parser))
    >>> [row.label for row in rows]
    ['Python path', 'Supported aliases', 'Config section']
    """
    rows = [
        ApiFactRow("Python path", linked_paragraph(info.qualified_name)),
        ApiFactRow("Supported aliases", build_chip_paragraph(list(info.aliases))),
        ApiFactRow(
            "Config section",
            _literal_paragraph(info.cls.config_section or "—"),
        ),
    ]
    if info.registered_via:
        rows.append(
            ApiFactRow(
                "Registered via",
                _literal_paragraph(f"app.{info.registered_via}()"),
            ),
        )
    return rows


def _render_parser(
    directive: SphinxDirective,
    info: ParserInfo,
    *,
    no_index: bool = False,
) -> list[nodes.Node]:
    """Render one parser entry through the shared component pipeline."""
    return render_component_nodes(
        directive,
        objtype=PARSER,
        path=info.qualified_name,
        summary=_summary(info.cls),
        fact_rows=_parser_fact_rows(info),
        badge_group=build_kind_badge_group(PARSER),
        no_index=no_index,
    )


class AutoParser(SphinxDirective):
    """Render documentation for a single parser class."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        info = discover_parser(self.arguments[0])
        return _render_parser(self, info, no_index="no-index" in self.options)


class AutoParsers(SphinxDirective):
    """Render documentation for every parser a module defines or registers."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        no_index = "no-index" in self.options
        results: list[nodes.Node] = []
        for info in discover_parsers(self.arguments[0]):
            results.extend(_render_parser(self, info, no_index=no_index))
        return results
