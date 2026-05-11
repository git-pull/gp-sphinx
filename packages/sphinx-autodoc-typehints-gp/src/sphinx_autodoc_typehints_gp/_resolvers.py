"""Shared resolver catalog for parameter and data/attribute defaults.

This module hosts the resolver Protocol and the built-in resolver
catalog used by both Site B (parameter-default rewriting in
:mod:`._param_defaults`) and Site A (data/attribute ``:value:``
curation in :mod:`._data_defaults`). Stage C's xref transform
(:mod:`._default_xref_transform`) does *not* consume these
resolvers — it is a node-tree pass that operates on already-rendered
text — so the catalog stays scoped to the two text-replacement
sites.

The surface is **private** (the leading underscore in the module
name): consumers should import from
:mod:`sphinx_autodoc_typehints_gp` re-exports if a public API is
ever needed. The empirical inventory in
``notes/defaults-discovery-d1.md`` shows the workspace's resolver
needs are homogeneous (factory-sentinel + truncation), so no
external registration mechanism is shipped today. If a downstream
consumer surfaces a divergent need, expose ``add_default_resolver``
through ``extension.setup()`` then.
"""

from __future__ import annotations

import typing as t


class ResolveContext(t.NamedTuple):
    """Context passed to each :class:`Resolver` in the chain.

    Attributes
    ----------
    value : object
        The live Python object: a callable for ``default_factory``
        cases, the raw default for direct-value cases, or the
        documented attribute's value for Site A.
    kind : str
        One of ``'param'``, ``'data'``, ``'attribute'``. Resolvers
        check this to scope themselves to the right site.
    qualname : str
        Fully qualified name of the documented object, e.g.
        ``'libtmux.constants.HookEventDataclass.__init__'``.
    param_name : str | None
        Set when ``kind == 'param'``; ``None`` for Site A.
    default_repr : str
        Sphinx's stock ``object_description`` of ``value`` (Site A)
        or the literal string ``'<factory>'`` (Site B's
        :class:`DataclassFactoryRepr` path). Resolvers can use this
        as a fallback or input string.
    """

    value: object
    kind: str
    qualname: str
    param_name: str | None
    default_repr: str


class Resolver(t.Protocol):
    """Compute a symbolic source-text string for a default value.

    Resolvers are run in priority order; the first non-``None``
    result wins. Return ``None`` to defer. Return ``""`` to suppress
    (Site A only — parameter defaults cannot be suppressed).
    """

    def __call__(self, ctx: ResolveContext) -> str | None:
        """Return the chosen text or ``None`` to defer."""
        ...


def run_chain(
    ctx: ResolveContext,
    resolvers: tuple[Resolver, ...],
) -> str | None:
    """Run *resolvers* in order and return the first non-``None`` result.

    Examples
    --------
    >>> ctx = ResolveContext(
    ...     value=list,
    ...     kind='param',
    ...     qualname='Foo.__init__',
    ...     param_name='items',
    ...     default_repr='<factory>',
    ... )
    >>> run_chain(ctx, (DataclassFactoryRepr(),))
    '[]'
    """
    for resolver in resolvers:
        result = resolver(ctx)
        if result is not None:
            return result
    return None


class DataclassFactoryRepr:
    """Render :func:`dataclasses.field` ``default_factory`` symbolically.

    Recognises stdlib container constructors (``list``, ``dict``,
    ``set``, ``frozenset``, ``tuple``) and named callable types.
    Defers (returns ``None``) on lambdas and unrecognised
    factories, leaving Sphinx's stock ``<factory>`` rendering in
    place.

    Examples
    --------
    >>> r = DataclassFactoryRepr()
    >>> ctx = ResolveContext(
    ...     value=list,
    ...     kind='param',
    ...     qualname='Foo.__init__',
    ...     param_name='items',
    ...     default_repr='<factory>',
    ... )
    >>> r(ctx)
    '[]'
    >>> r(ctx._replace(value=dict))
    '{}'
    >>> r(ctx._replace(value=set))
    'set()'
    >>> r(ctx._replace(value=lambda: 1)) is None
    True
    """

    _BUILTIN_LITERALS: t.ClassVar[dict[type, str]] = {
        list: "[]",
        dict: "{}",
        set: "set()",
        frozenset: "frozenset()",
        tuple: "()",
    }

    def __call__(self, ctx: ResolveContext) -> str | None:
        """Resolve a ``default_factory`` callable to its source text."""
        if ctx.kind != "param":
            return None
        factory = ctx.value
        if isinstance(factory, type):
            literal = self._BUILTIN_LITERALS.get(factory)
            if literal is not None:
                return literal
            name = getattr(factory, "__name__", None)
            if name and name != "<lambda>":
                return f"{name}()"
        return None


class TruncateLongRepr:
    """Truncate long Site A ``:value:`` text.

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
