"""Custom Documenter classes that curate data/attribute ``:value:`` text.

Sphinx's stock :class:`DataDocumenter` and :class:`AttributeDocumenter`
emit a ``:value: <objrepr>`` line where ``<objrepr>`` comes from
:func:`sphinx.util.inspect.object_description` — the raw ``repr()``
with memory addresses stripped. For large module-level constants
(libvcs's ``DEFAULT_RULES`` is the canonical example: a 5 738-char
list of dataclasses) this produces unreadable signature blocks.

This module overrides the documenters to run a resolver chain over
the ``:value:`` text. Each resolver may:

- return ``None`` to defer to the next resolver (chain falls through
  to Sphinx's stock ``:value: <objrepr>``);
- return an empty string to suppress the ``:value:`` line entirely
  (equivalent to ``:no-value:`` for that one attribute);
- return a non-empty string to replace the value text (e.g.
  ``<…truncated, 5738 chars>``).

The built-in catalog (seeded by D1 evidence) ships
:class:`TruncateLongRepr` only; richer resolvers
(``ListOfDataclassesSummary``, ``CompiledRegexRepr``) belong to D5
once the framework decision is made.
"""

from __future__ import annotations

import typing as t

from sphinx.ext.autodoc import AttributeDocumenter, DataDocumenter, ModuleDocumenter

from sphinx_autodoc_typehints_gp._documented_fields import (
    FieldDocFallbackMixin,
    active_module_field,
)
from sphinx_autodoc_typehints_gp._resolvers import (
    ResolveContext,
    Resolver,
    TruncateLongRepr,
    run_chain,
)

_VALUE_PREFIX: t.Final = "   :value: "

_DATA_RESOLVERS: tuple[Resolver, ...] = (TruncateLongRepr(),)


def _curate_value_line(
    documenter: DataDocumenter | AttributeDocumenter,
    line: str,
) -> str | None:
    """Decide what to do with a ``:value: …`` directive line.

    Returns
    -------
        - ``None`` to keep the original line.
        - ``""`` to suppress (do not emit any ``:value:`` line).
        - A new line string starting with ``"   :value: "`` to replace.

    Examples
    --------
    >>> import types
    >>> stub = types.SimpleNamespace(
    ...     config=types.SimpleNamespace(gp_typehints_curate_data_defaults=True),
    ...     object='admin',
    ...     objtype='data',
    ...     fullname='mod.SHORT',
    ... )
    >>> _curate_value_line(stub, "   :module: mod") is None
    True
    >>> _curate_value_line(stub, "   :value: 'admin'") is None
    True
    >>> long_repr = repr(['x' * 50] * 10)
    >>> stub.object = ['x' * 50] * 10
    >>> stub.fullname = 'mod.LONG'
    >>> _curate_value_line(stub, f"   :value: {long_repr}")
    '   :value: <...truncated, 540 chars>'
    >>> stub.config.gp_typehints_curate_data_defaults = False
    >>> _curate_value_line(stub, f"   :value: {long_repr}") is None
    True
    """
    if not line.startswith(_VALUE_PREFIX):
        return None
    config_flag = getattr(documenter.config, "gp_typehints_curate_data_defaults", True)
    if not config_flag:
        return None
    raw_repr = line[len(_VALUE_PREFIX) :]
    ctx = ResolveContext(
        value=documenter.object,
        kind=documenter.objtype,
        qualname=documenter.fullname or "<unknown>",
        param_name=None,
        default_repr=raw_repr,
    )
    text = run_chain(ctx, _DATA_RESOLVERS)
    if text is None:
        return None
    if text == "":
        return ""
    return f"{_VALUE_PREFIX}{text}"


class GpDataDocumenter(FieldDocFallbackMixin, DataDocumenter):
    """``DataDocumenter`` that curates ``:value:`` text via the resolver chain.

    Also documents a module constant the module docstring described.
    Autodoc reaches for its data documenter only for a name the source
    annotates or comments; a name an ``Attributes`` section describes is
    just as deliberate, and routing it here is what lets the entry keep
    the value only the live module can supply.
    """

    objtype = "data"
    priority = DataDocumenter.priority + 1

    @classmethod
    def can_document_member(
        cls,
        member: t.Any,
        membername: str,
        isattr: bool,
        parent: t.Any,
    ) -> bool:
        """Return whether this documenter should render *membername*.

        Parameters
        ----------
        member : typing.Any
            The member object under consideration.
        membername : str
            Bare member name.
        isattr : bool
            Whether autodoc classified the member as an attribute.
        parent : typing.Any
            Documenter of the object the member belongs to.

        Returns
        -------
        bool
            Whether the member is module data this documenter renders.

        Examples
        --------
        >>> GpDataDocumenter.can_document_member(1, "LIMIT", False, None)
        False
        """
        if super().can_document_member(member, membername, isattr, parent):
            return True
        return isinstance(parent, ModuleDocumenter) and active_module_field(membername)

    def add_line(self, line: str, source: str, *lineno: int) -> None:
        """Curate ``:value:`` lines; pass everything else through unchanged."""
        result = _curate_value_line(self, line)
        if result is None:
            super().add_line(line, source, *lineno)
        elif result == "":
            return
        else:
            super().add_line(result, source, *lineno)


class GpAttributeDocumenter(FieldDocFallbackMixin, AttributeDocumenter):  # type: ignore[misc]
    """``AttributeDocumenter`` that curates ``:value:`` text via the resolver chain."""

    objtype = "attribute"
    priority = AttributeDocumenter.priority + 1

    def update_annotations(self, parent: t.Any) -> None:
        """Merge type-comment annotations, except into a typed dictionary.

        Autodoc materializes ``parent.__annotations__`` so a ``# type:``
        comment can join it. A :class:`typing.TypedDict` computes its
        annotations lazily and merges every base's, so materializing a
        base's annotations severs that merge and every key the subclass
        inherits disappears from the page. A typed dictionary declares its
        keys by annotation alone and has no type comments to merge, so it
        keeps its own lazy mapping.

        Parameters
        ----------
        parent : typing.Any
            Class the member being documented belongs to.

        Examples
        --------
        >>> GpAttributeDocumenter.update_annotations  # doctest: +ELLIPSIS
        <function GpAttributeDocumenter.update_annotations at 0x...>
        """
        if isinstance(parent, type) and t.is_typeddict(parent):
            return
        super().update_annotations(parent)

    def add_line(self, line: str, source: str, *lineno: int) -> None:
        """Curate ``:value:`` lines; pass everything else through unchanged."""
        result = _curate_value_line(self, line)
        if result is None:
            super().add_line(line, source, *lineno)
        elif result == "":
            return
        else:
            super().add_line(result, source, *lineno)
