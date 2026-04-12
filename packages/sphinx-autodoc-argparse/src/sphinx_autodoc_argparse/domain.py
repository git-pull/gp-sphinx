"""The argparse Sphinx domain.

Registers four object types (``program``, ``option``, ``subcommand``,
``positional``) with matching cross-reference roles, two auto-generated
indices (programs, options), and the standard lifecycle hooks Sphinx
expects from a parallel-safe domain.

The renderer wires into this domain via ``note_program`` /
``note_option`` / ``note_subcommand`` / ``note_positional`` alongside
the existing ``std:cmdoption`` registration, so ``:argparse:option:``
cross-references and the two domain indices work without breaking
``:option:`` intersphinx consumers.

Examples
--------
>>> from sphinx_autodoc_argparse.domain import ArgparseDomain
>>> ArgparseDomain.name
'argparse'
>>> sorted(ArgparseDomain.object_types)
['option', 'positional', 'program', 'subcommand']
>>> sorted(ArgparseDomain.roles)
['option', 'positional', 'program', 'subcommand']
>>> [cls.name for cls in ArgparseDomain.indices]
['programsindex', 'optionsindex']
"""

from __future__ import annotations

import typing as t

from sphinx.domains import Domain, Index, IndexEntry, ObjType
from sphinx.locale import _
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode

if t.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Set

    from docutils import nodes
    from docutils.nodes import Element
    from sphinx.addnodes import pending_xref
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment


#: Object type name used for programs (top-level CLIs).
PROGRAM = "program"
#: Object type name used for options (optional flags like ``--verbose``).
OPTION = "option"
#: Object type name used for subcommands (e.g. ``myapp sub``).
SUBCOMMAND = "subcommand"
#: Object type name used for positional arguments (e.g. ``myapp FILE``).
POSITIONAL = "positional"

#: All object type names in a single tuple for iteration.
OBJECT_TYPES: tuple[str, ...] = (PROGRAM, OPTION, SUBCOMMAND, POSITIONAL)


class ArgparseProgramsIndex(Index):
    """Alphabetical index of every registered argparse program.

    The generated page lives at ``argparse-programsindex.html`` and can be
    linked via ``:ref:`argparse-programsindex```.

    Examples
    --------
    >>> ArgparseProgramsIndex.name
    'programsindex'
    >>> str(ArgparseProgramsIndex.localname)
    'Argparse programs index'
    """

    name = "programsindex"
    localname = _("Argparse programs index")
    shortname = _("programs")

    def generate(
        self,
        docnames: Iterable[str] | None = None,
    ) -> tuple[list[tuple[str, list[IndexEntry]]], bool]:
        """Build the programs index entries grouped by first-letter heading."""
        content: dict[str, list[IndexEntry]] = {}
        allowed = set(docnames) if docnames is not None else None

        programs: dict[str, tuple[str, str]] = self.domain.data.get("programs", {})
        for name in sorted(programs):
            docname, anchor = programs[name]
            if allowed is not None and docname not in allowed:
                continue
            letter = (name[:1] or "_").lower()
            content.setdefault(letter, []).append(
                IndexEntry(
                    name=name,
                    subtype=0,
                    docname=docname,
                    anchor=anchor,
                    extra="",
                    qualifier="",
                    descr=_("program"),
                ),
            )

        return (
            sorted(content.items()),
            False,
        )


class ArgparseOptionsIndex(Index):
    """Per-program grouped index of every registered argparse option.

    Each program heading groups the options that program defines, sorted
    alphabetically. The generated page lives at
    ``argparse-optionsindex.html`` and can be linked via
    ``:ref:`argparse-optionsindex```.

    Examples
    --------
    >>> ArgparseOptionsIndex.name
    'optionsindex'
    >>> str(ArgparseOptionsIndex.localname)
    'Argparse options index'
    """

    name = "optionsindex"
    localname = _("Argparse options index")
    shortname = _("options")

    def generate(
        self,
        docnames: Iterable[str] | None = None,
    ) -> tuple[list[tuple[str, list[IndexEntry]]], bool]:
        """Build the options index entries grouped by program heading."""
        content: dict[str, list[IndexEntry]] = {}
        allowed = set(docnames) if docnames is not None else None

        options: dict[tuple[str, str], tuple[str, str]] = self.domain.data.get(
            "options",
            {},
        )
        for program, name in sorted(options):
            docname, anchor = options[program, name]
            if allowed is not None and docname not in allowed:
                continue
            heading = program or "-"
            content.setdefault(heading, []).append(
                IndexEntry(
                    name=name,
                    subtype=0,
                    docname=docname,
                    anchor=anchor,
                    extra="",
                    qualifier=program,
                    descr=_("option"),
                ),
            )

        return (
            sorted(content.items()),
            True,
        )


class ArgparseDomain(Domain):
    """Sphinx domain for argparse-based CLI documentation.

    Stores four dictionaries under ``env.domaindata["argparse"]``:

    * ``programs[name] = (docname, anchor)``
    * ``options[(program, name)] = (docname, anchor)``
    * ``subcommands[(program, name)] = (docname, anchor)``
    * ``positionals[(program, name)] = (docname, anchor)``

    Programs are keyed by their full dotted/space-joined name
    (``"myapp"``, ``"myapp sub"``). Options, subcommands, and positionals
    are keyed by ``(program, local_name)`` tuples so the same flag name
    may exist under multiple programs without collision.

    Examples
    --------
    >>> ArgparseDomain.name
    'argparse'
    >>> ArgparseDomain.data_version
    0
    """

    name = "argparse"
    label = "Argparse CLI"

    object_types = {  # noqa: RUF012 — matches upstream sphinx.domains.Domain shape
        PROGRAM: ObjType(_("program"), PROGRAM),
        OPTION: ObjType(_("option"), OPTION),
        SUBCOMMAND: ObjType(_("subcommand"), SUBCOMMAND),
        POSITIONAL: ObjType(_("positional"), POSITIONAL),
    }

    directives: dict[str, t.Any] = {}  # noqa: RUF012

    roles = {  # noqa: RUF012 — XRefRole instances are safe to share across domains
        PROGRAM: XRefRole(),
        OPTION: XRefRole(),
        SUBCOMMAND: XRefRole(),
        POSITIONAL: XRefRole(),
    }

    indices = [  # noqa: RUF012 — matches upstream sphinx.domains.Domain shape
        ArgparseProgramsIndex,
        ArgparseOptionsIndex,
    ]

    initial_data = {  # noqa: RUF012 — matches upstream sphinx.domains.Domain shape
        "programs": {},
        "options": {},
        "subcommands": {},
        "positionals": {},
    }

    data_version = 0

    @property
    def programs(self) -> dict[str, tuple[str, str]]:
        """Programs keyed by name: ``name -> (docname, anchor)``."""
        return t.cast(
            "dict[str, tuple[str, str]]", self.data.setdefault("programs", {})
        )

    @property
    def options(self) -> dict[tuple[str, str], tuple[str, str]]:
        """Options keyed by ``(program, name) -> (docname, anchor)``."""
        return t.cast(
            "dict[tuple[str, str], tuple[str, str]]",
            self.data.setdefault("options", {}),
        )

    @property
    def subcommands(self) -> dict[tuple[str, str], tuple[str, str]]:
        """Subcommands keyed by ``(program, name) -> (docname, anchor)``."""
        return t.cast(
            "dict[tuple[str, str], tuple[str, str]]",
            self.data.setdefault("subcommands", {}),
        )

    @property
    def positionals(self) -> dict[tuple[str, str], tuple[str, str]]:
        """Positionals keyed by ``(program, name) -> (docname, anchor)``."""
        return t.cast(
            "dict[tuple[str, str], tuple[str, str]]",
            self.data.setdefault("positionals", {}),
        )

    def note_program(self, name: str, docname: str, anchor: str) -> None:
        """Record a program target in the domain data."""
        self.programs[name] = (docname, anchor)

    def note_option(
        self,
        program: str,
        name: str,
        docname: str,
        anchor: str,
    ) -> None:
        """Record an option target in the domain data."""
        self.options[program, name] = (docname, anchor)

    def note_subcommand(
        self,
        program: str,
        name: str,
        docname: str,
        anchor: str,
    ) -> None:
        """Record a subcommand target in the domain data."""
        self.subcommands[program, name] = (docname, anchor)

    def note_positional(
        self,
        program: str,
        name: str,
        docname: str,
        anchor: str,
    ) -> None:
        """Record a positional argument target in the domain data."""
        self.positionals[program, name] = (docname, anchor)

    def clear_doc(self, docname: str) -> None:
        """Drop every entry that came from *docname* so it can be re-built."""
        for program, (existing, _anchor) in list(self.programs.items()):
            if existing == docname:
                del self.programs[program]
        for key, (existing, _anchor) in list(self.options.items()):
            if existing == docname:
                del self.options[key]
        for key, (existing, _anchor) in list(self.subcommands.items()):
            if existing == docname:
                del self.subcommands[key]
        for key, (existing, _anchor) in list(self.positionals.items()):
            if existing == docname:
                del self.positionals[key]

    def merge_domaindata(
        self,
        docnames: Set[str],
        otherdata: dict[str, t.Any],
    ) -> None:
        """Merge sibling worker's ``domaindata`` under parallel builds."""
        for program, (docname, anchor) in otherdata.get("programs", {}).items():
            if docname in docnames:
                self.programs[program] = (docname, anchor)
        for key, (docname, anchor) in otherdata.get("options", {}).items():
            if docname in docnames:
                self.options[key] = (docname, anchor)
        for key, (docname, anchor) in otherdata.get("subcommands", {}).items():
            if docname in docnames:
                self.subcommands[key] = (docname, anchor)
        for key, (docname, anchor) in otherdata.get("positionals", {}).items():
            if docname in docnames:
                self.positionals[key] = (docname, anchor)

    def resolve_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder: Builder,
        typ: str,
        target: str,
        node: pending_xref,
        contnode: Element,
    ) -> nodes.reference | None:
        """Resolve a single typed cross-reference to a docutils reference."""
        match = self._lookup(typ, target)
        if match is None:
            return None
        todocname, anchor = match
        return make_refnode(
            builder,
            fromdocname,
            todocname,
            anchor,
            contnode,
            target,
        )

    def resolve_any_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder: Builder,
        target: str,
        node: pending_xref,
        contnode: Element,
    ) -> list[tuple[str, nodes.reference]]:
        """Resolve an untyped ``:any:`` cross-reference across object types."""
        results: list[tuple[str, nodes.reference]] = []
        for objtype in OBJECT_TYPES:
            match = self._lookup(objtype, target)
            if match is None:
                continue
            todocname, anchor = match
            results.append(
                (
                    f"argparse:{objtype}",
                    make_refnode(
                        builder,
                        fromdocname,
                        todocname,
                        anchor,
                        contnode,
                        target,
                    ),
                ),
            )
        return results

    def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:
        """Yield ``(name, dispname, type, docname, anchor, priority)`` rows."""
        for name, (docname, anchor) in self.programs.items():
            yield name, name, PROGRAM, docname, anchor, 1
        for (program, name), (docname, anchor) in self.options.items():
            dispname = f"{program} {name}" if program else name
            yield dispname, dispname, OPTION, docname, anchor, 1
        for (program, name), (docname, anchor) in self.subcommands.items():
            dispname = f"{program} {name}" if program else name
            yield dispname, dispname, SUBCOMMAND, docname, anchor, 1
        for (program, name), (docname, anchor) in self.positionals.items():
            dispname = f"{program} {name}" if program else name
            yield dispname, dispname, POSITIONAL, docname, anchor, 1

    def _lookup(self, typ: str, target: str) -> tuple[str, str] | None:
        """Look up *target* in *typ*'s table, supporting composite option keys.

        Options, subcommands, and positionals are stored under
        ``(program, name)`` keys. Authors commonly write the full
        whitespace-joined form (e.g. ``myapp --verbose``); split the
        rightmost whitespace token to map that back to the tuple key.
        """
        if typ == PROGRAM:
            if target in self.programs:
                return self.programs[target]
            return None

        table = {
            OPTION: self.options,
            SUBCOMMAND: self.subcommands,
            POSITIONAL: self.positionals,
        }.get(typ)
        if table is None:
            return None

        # Exact tuple key from a pre-split target like "myapp sub --verbose"
        if " " in target:
            program, _, name = target.rpartition(" ")
            if (program, name) in table:
                return table[program, name]

        # Fallback: search every program for an exact name hit
        for (program, name), value in table.items():
            if target == name or target == f"{program} {name}":
                return value
        return None
