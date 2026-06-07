"""The sphinxext components Sphinx domain.

Registers two object types (``builder``, ``domain``) with matching
cross-reference roles, one grouped-by-objtype index, and the standard
lifecycle hooks Sphinx expects from a parallel-safe domain.

The component autodoc directives wire into this domain by generating
``.. sphinxext:<objtype>:: dotted.path.ClassName`` markup, so the
parsed ``desc`` nodes natively carry ``domain="sphinxext"`` and a
per-type ``objtype`` — the shared layout and badge pipelines key off
both.

Examples
--------
>>> from sphinx_autodoc_sphinx.domain import SphinxExtDomain
>>> SphinxExtDomain.name
'sphinxext'
>>> sorted(SphinxExtDomain.object_types)
['builder', 'domain']
>>> sorted(SphinxExtDomain.roles) == sorted(SphinxExtDomain.object_types)
True
>>> [cls.name for cls in SphinxExtDomain.indices]
['componentindex']
"""

from __future__ import annotations

import typing as t

from docutils.parsers.rst import directives
from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, Index, IndexEntry, ObjType
from sphinx.locale import _
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_id, make_refnode

if t.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Set

    from docutils import nodes
    from docutils.nodes import Element
    from sphinx.addnodes import pending_xref
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import OptionSpec


#: Object type name used for Sphinx builders.
BUILDER = "builder"
#: Object type name used for Sphinx domains.
DOMAIN = "domain"

#: All object type names in a single tuple for iteration.
OBJECT_TYPES: tuple[str, ...] = (BUILDER, DOMAIN)

#: Index group headings keyed by object type.
_INDEX_HEADINGS: dict[str, str] = {
    BUILDER: "Builders",
    DOMAIN: "Domains",
}


def split_component_path(path: str) -> tuple[str, str]:
    """Split a dotted component path into ``(module, class_name)``.

    Examples
    --------
    >>> split_component_path("sphinx.builders.dummy.DummyBuilder")
    ('sphinx.builders.dummy', 'DummyBuilder')

    >>> split_component_path("DummyBuilder")
    ('', 'DummyBuilder')
    """
    module_name, _sep, class_name = path.rpartition(".")
    return module_name, class_name


class SphinxExtComponentDescription(ObjectDescription[str]):
    """Object description for one Sphinx extension component class.

    The signature argument is a dotted Python path
    (``pkg.module.ClassName``); the module prefix renders as
    ``desc_addname`` and the class name as ``desc_name``, matching the
    ``py:class`` visual structure. The anchor and cross-reference
    target are owned by :class:`SphinxExtDomain`.
    """

    option_spec: t.ClassVar[OptionSpec] = {
        "no-index": directives.flag,
    }

    def handle_signature(
        self,
        sig: str,
        sig_node: addnodes.desc_signature,
    ) -> str:
        """Render *sig* (a dotted path) into the signature node."""
        path = sig.strip()
        module_name, class_name = split_component_path(path)
        if module_name:
            sig_node += addnodes.desc_addname(
                f"{module_name}.",
                f"{module_name}.",
            )
        sig_node += addnodes.desc_name(class_name, class_name)
        sig_node["fullname"] = path
        return path

    def _object_hierarchy_parts(
        self,
        sig_node: addnodes.desc_signature,
    ) -> tuple[str, ...]:
        """Return the TOC hierarchy parts for *sig_node*."""
        return (str(sig_node["fullname"]),)

    def _toc_entry_name(self, sig_node: addnodes.desc_signature) -> str:
        """Return the local-TOC entry text (the bare class name)."""
        if not sig_node.get("_toc_parts"):
            return ""
        (name,) = sig_node["_toc_parts"]
        return split_component_path(str(name))[1]

    def add_target_and_index(
        self,
        name: str,
        sig: str,
        signode: addnodes.desc_signature,
    ) -> None:
        """Create the anchor and note the component in the domain."""
        node_id = make_id(
            self.env,
            self.state.document,
            f"sphinxext-{self.objtype}",
            name,
        )
        signode["ids"].append(node_id)
        self.state.document.note_explicit_target(signode)
        domain = t.cast("SphinxExtDomain", self.env.domains[SphinxExtDomain.name])
        domain.note_component(self.objtype, name, self.env.docname, node_id)


class SphinxExtComponentIndex(Index):
    """Grouped-by-objtype index of every registered extension component.

    The generated page lives at ``sphinxext-componentindex.html`` and
    can be linked via ``:ref:`sphinxext-componentindex```.

    Examples
    --------
    >>> SphinxExtComponentIndex.name
    'componentindex'
    >>> str(SphinxExtComponentIndex.localname)
    'Sphinx extension components index'
    """

    name = "componentindex"
    localname = _("Sphinx extension components index")
    shortname = _("components")

    def generate(
        self,
        docnames: Iterable[str] | None = None,
    ) -> tuple[list[tuple[str, list[IndexEntry]]], bool]:
        """Build the component index entries grouped by object type."""
        content: dict[str, list[IndexEntry]] = {}
        allowed = set(docnames) if docnames is not None else None

        for objtype in OBJECT_TYPES:
            table: dict[str, tuple[str, str]] = self.domain.data.get(objtype, {})
            for name in sorted(table):
                docname, anchor = table[name]
                if allowed is not None and docname not in allowed:
                    continue
                heading = _INDEX_HEADINGS[objtype]
                content.setdefault(heading, []).append(
                    IndexEntry(
                        name=name,
                        subtype=0,
                        docname=docname,
                        anchor=anchor,
                        extra="",
                        qualifier="",
                        descr=_(objtype),
                    ),
                )

        return (
            sorted(content.items()),
            True,
        )


class SphinxExtDomain(Domain):
    """Sphinx domain for extension component documentation.

    Stores one dictionary per object type under
    ``env.domaindata["sphinxext"]``::

        data[objtype][qualified_name] = (docname, anchor)

    Components are keyed by their fully-qualified dotted Python path
    (``"pkg.module.ClassName"``), which is unique per class. Lookup
    additionally accepts the bare class name when it matches exactly
    one registered component.

    Examples
    --------
    >>> SphinxExtDomain.name
    'sphinxext'
    >>> SphinxExtDomain.data_version
    0
    """

    name = "sphinxext"
    label = "Sphinx extensions"

    object_types = {  # noqa: RUF012 — matches upstream sphinx.domains.Domain shape
        BUILDER: ObjType(_("builder"), BUILDER),
        DOMAIN: ObjType(_("domain"), DOMAIN),
    }

    directives = {  # noqa: RUF012 — matches upstream sphinx.domains.Domain shape
        BUILDER: SphinxExtComponentDescription,
        DOMAIN: SphinxExtComponentDescription,
    }

    roles = {  # noqa: RUF012 — XRefRole instances are safe to share across domains
        BUILDER: XRefRole(warn_dangling=True),
        DOMAIN: XRefRole(warn_dangling=True),
    }

    indices = [  # noqa: RUF012 — matches upstream sphinx.domains.Domain shape
        SphinxExtComponentIndex,
    ]

    initial_data = {  # noqa: RUF012 — matches upstream sphinx.domains.Domain shape
        BUILDER: {},
        DOMAIN: {},
    }

    data_version = 0

    def components(self, objtype: str) -> dict[str, tuple[str, str]]:
        """Return *objtype*'s table: ``qualified_name -> (docname, anchor)``."""
        return t.cast(
            "dict[str, tuple[str, str]]",
            self.data.setdefault(objtype, {}),
        )

    def note_component(
        self,
        objtype: str,
        name: str,
        docname: str,
        anchor: str,
    ) -> None:
        """Record a component target in the domain data."""
        self.components(objtype)[name] = (docname, anchor)

    def clear_doc(self, docname: str) -> None:
        """Drop every entry that came from *docname* so it can be re-built."""
        for objtype in OBJECT_TYPES:
            table = self.components(objtype)
            for name, (existing, _anchor) in list(table.items()):
                if existing == docname:
                    del table[name]

    def merge_domaindata(
        self,
        docnames: Set[str],
        otherdata: dict[str, t.Any],
    ) -> None:
        """Merge sibling worker's ``domaindata`` under parallel builds."""
        for objtype in OBJECT_TYPES:
            for name, (docname, anchor) in otherdata.get(objtype, {}).items():
                if docname in docnames:
                    self.components(objtype)[name] = (docname, anchor)

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
                    f"sphinxext:{objtype}",
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
        for objtype in OBJECT_TYPES:
            for name, (docname, anchor) in self.components(objtype).items():
                yield name, name, objtype, docname, anchor, 1

    def _lookup(self, typ: str, target: str) -> tuple[str, str] | None:
        """Look up *target* in *typ*'s table, accepting bare class names.

        Components are stored under fully-qualified dotted paths.
        Authors commonly write the bare class name (``DummyBuilder``);
        fall back to a suffix match when it identifies exactly one
        component.
        """
        if typ not in OBJECT_TYPES:
            return None
        table = self.components(typ)
        if target in table:
            return table[target]
        candidates = [
            value
            for name, value in table.items()
            if split_component_path(name)[1] == target
        ]
        if len(candidates) == 1:
            return candidates[0]
        return None
