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

from sphinx.ext.autodoc import AttributeDocumenter, DataDocumenter

from sphinx_autodoc_typehints_gp._param_defaults import (
    ResolveContext,
    Resolver,
    _run_chain,
)

_VALUE_PREFIX: t.Final = "   :value: "


class TruncateLongRepr:
    """Truncate long ``:value:`` text.

    Returns ``None`` (defer) for parameter contexts and for short
    reprs; returns ``"<...truncated, N chars>"`` for reprs over the
    threshold.

    Examples
    --------
    >>> r = TruncateLongRepr(threshold=10)
    >>> r(ResolveContext(
    ...     value=None,
    ...     kind='data',
    ...     qualname='mod.X',
    ...     param_name=None,
    ...     default_repr='[1, 2]',
    ... )) is None
    True
    >>> r(ResolveContext(
    ...     value=None,
    ...     kind='data',
    ...     qualname='mod.X',
    ...     param_name=None,
    ...     default_repr='this string is longer than ten characters',
    ... ))
    '<...truncated, 41 chars>'
    """

    def __init__(self, threshold: int = 200) -> None:
        self.threshold = threshold

    def __call__(self, ctx: ResolveContext) -> str | None:
        """Return a truncated marker if *ctx.default_repr* is too long."""
        if ctx.kind not in {"data", "attribute"}:
            return None
        text = ctx.default_repr
        if not text or len(text) <= self.threshold:
            return None
        return f"<...truncated, {len(text)} chars>"


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
    text = _run_chain(ctx, _DATA_RESOLVERS)
    if text is None:
        return None
    if text == "":
        return ""
    return f"{_VALUE_PREFIX}{text}"


class GpDataDocumenter(DataDocumenter):
    """``DataDocumenter`` that curates ``:value:`` text via the resolver chain."""

    objtype = "data"
    priority = DataDocumenter.priority + 1

    def add_line(self, line: str, source: str, *lineno: int) -> None:
        """Curate ``:value:`` lines; pass everything else through unchanged."""
        result = _curate_value_line(self, line)
        if result is None:
            super().add_line(line, source, *lineno)
        elif result == "":
            return
        else:
            super().add_line(result, source, *lineno)


class GpAttributeDocumenter(AttributeDocumenter):
    """``AttributeDocumenter`` that curates ``:value:`` text via the resolver chain."""

    objtype = "attribute"
    priority = AttributeDocumenter.priority + 1

    def add_line(self, line: str, source: str, *lineno: int) -> None:
        """Curate ``:value:`` lines; pass everything else through unchanged."""
        result = _curate_value_line(self, line)
        if result is None:
            super().add_line(line, source, *lineno)
        elif result == "":
            return
        else:
            super().add_line(result, source, *lineno)
