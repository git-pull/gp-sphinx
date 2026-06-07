"""Rendering directives for Sphinx domain documentation."""

from __future__ import annotations

import inspect
import typing as t
from dataclasses import dataclass

from docutils.parsers.rst import directives
from sphinx.domains import Domain
from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_sphinx._badges import build_domain_badge_group
from sphinx_autodoc_sphinx._components import (
    component_classes,
    component_summary,
    import_component,
    linked_paragraph,
    render_component_nodes,
    replay_setup,
)
from sphinx_autodoc_sphinx._directives import _literal_paragraph
from sphinx_autodoc_sphinx.domain import DOMAIN
from sphinx_ux_autodoc_layout import ApiFactRow, build_chip_paragraph

if t.TYPE_CHECKING:
    from docutils import nodes
    from sphinx.util.typing import OptionSpec


@dataclass(frozen=True)
class DomainInfo:
    """Recorded metadata for one documented domain class.

    Examples
    --------
    >>> from sphinx_autodoc_argparse.domain import ArgparseDomain
    >>> info = DomainInfo(cls=ArgparseDomain, registered=True)
    >>> info.qualified_name
    'sphinx_autodoc_argparse.domain.ArgparseDomain'
    >>> info.domain_name
    'argparse'
    """

    cls: type[Domain]
    registered: bool = False

    @property
    def qualified_name(self) -> str:
        """Return the fully-qualified dotted path for the class.

        Examples
        --------
        >>> from sphinx_autodoc_argparse.domain import ArgparseDomain
        >>> DomainInfo(cls=ArgparseDomain).qualified_name
        'sphinx_autodoc_argparse.domain.ArgparseDomain'
        """
        return f"{self.cls.__module__}.{self.cls.__name__}"

    @property
    def domain_name(self) -> str:
        """Return the domain's registered name (the role prefix).

        Examples
        --------
        >>> from sphinx_autodoc_argparse.domain import ArgparseDomain
        >>> DomainInfo(cls=ArgparseDomain).domain_name
        'argparse'
        """
        return str(self.cls.name)


def _domains_from_calls(
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]],
) -> list[DomainInfo]:
    """Extract domain metadata from recorded ``add_domain`` calls.

    Examples
    --------
    >>> from sphinx_autodoc_argparse.domain import ArgparseDomain
    >>> infos = _domains_from_calls(
    ...     [
    ...         ("add_domain", (ArgparseDomain,), {}),
    ...         ("add_directive", ("noise", object), {}),
    ...     ],
    ... )
    >>> [(info.cls.__name__, info.registered) for info in infos]
    [('ArgparseDomain', True)]
    """
    infos: list[DomainInfo] = []
    seen: set[type[Domain]] = set()
    for call_name, args, _kwargs in calls:
        if call_name != "add_domain" or len(args) < 1:
            continue
        cls = args[0]
        if not (inspect.isclass(cls) and issubclass(cls, Domain)):
            continue
        if cls in seen:
            continue
        seen.add(cls)
        infos.append(DomainInfo(cls=cls, registered=True))
    return infos


def discover_domains(module_name: str) -> list[DomainInfo]:
    """Return domains a module registers, or defines as a fallback.

    Replays the module's ``setup()`` against a recorder so domains
    surface with their ``app.add_domain()`` registration; falls back
    to scanning the module for public
    :class:`~sphinx.domains.Domain` subclasses.

    Examples
    --------
    >>> infos = discover_domains("sphinx_autodoc_docutils")
    >>> [(info.cls.__name__, info.registered) for info in infos]
    [('DocutilsDomain', True)]

    >>> infos = discover_domains("sphinx_autodoc_argparse.domain")
    >>> [(info.cls.__name__, info.registered) for info in infos]
    [('ArgparseDomain', False)]

    >>> discover_domains("sphinx_fonts")
    []
    """
    recorder = replay_setup(module_name)
    if recorder is not None:
        infos = _domains_from_calls(recorder.calls)
        if infos:
            return infos
    return [DomainInfo(cls=cls) for cls in component_classes(module_name, Domain)]


def discover_domain(path: str) -> DomainInfo:
    """Return one domain from a fully-qualified dotted path.

    Examples
    --------
    >>> info = discover_domain("sphinx_autodoc_argparse.domain.ArgparseDomain")
    >>> info.domain_name
    'argparse'
    """
    cls = t.cast("type[Domain]", import_component(path))
    for info in discover_domains(cls.__module__):
        if info.cls is cls:
            return info
    return DomainInfo(cls=cls)


def _domain_fact_rows(info: DomainInfo) -> list[ApiFactRow]:
    """Return shared fact rows for one autodocumented domain.

    Examples
    --------
    >>> from sphinx_autodoc_argparse.domain import ArgparseDomain
    >>> rows = _domain_fact_rows(DomainInfo(cls=ArgparseDomain))
    >>> [row.label for row in rows]  # doctest: +NORMALIZE_WHITESPACE
    ['Python path', 'Domain name', 'Label', 'Object types', 'Roles',
     'Directives', 'Indices']
    """
    cls = info.cls
    return [
        ApiFactRow("Python path", linked_paragraph(info.qualified_name)),
        ApiFactRow("Domain name", _literal_paragraph(info.domain_name or "—")),
        # str() unwraps the lazy gettext proxy Sphinx domains use.
        ApiFactRow("Label", _literal_paragraph(str(cls.label) or "—")),
        ApiFactRow("Object types", build_chip_paragraph(sorted(cls.object_types))),
        ApiFactRow("Roles", build_chip_paragraph(sorted(cls.roles))),
        ApiFactRow("Directives", build_chip_paragraph(sorted(cls.directives))),
        ApiFactRow(
            "Indices",
            build_chip_paragraph([index.name for index in cls.indices]),
        ),
    ]


def _render_domain(
    directive: SphinxDirective,
    info: DomainInfo,
    *,
    no_index: bool = False,
) -> list[nodes.Node]:
    """Render one domain entry through the shared component pipeline."""
    return render_component_nodes(
        directive,
        objtype=DOMAIN,
        path=info.qualified_name,
        summary=component_summary(info.cls),
        fact_rows=_domain_fact_rows(info),
        badge_group=build_domain_badge_group(info.domain_name),
        no_index=no_index,
    )


class AutoDomain(SphinxDirective):
    """Render documentation for a single domain class."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        info = discover_domain(self.arguments[0])
        return _render_domain(self, info, no_index="no-index" in self.options)


class AutoDomains(SphinxDirective):
    """Render documentation for every domain a package registers.

    Accepts either an extension package (whose ``setup()`` runs against
    a recorder so each ``app.add_domain(cls)`` call surfaces) or a
    domain-defining module (introspected for ``Domain`` subclasses).
    """

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        no_index = "no-index" in self.options
        results: list[nodes.Node] = []
        for info in discover_domains(self.arguments[0]):
            results.extend(_render_domain(self, info, no_index=no_index))
        return results
