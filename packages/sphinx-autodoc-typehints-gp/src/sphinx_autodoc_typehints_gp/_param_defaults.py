"""Resolver chain for synthetic-init parameter defaults.

Sphinx's ``autodoc_preserve_defaults`` flag handles regular function
and method signatures via :func:`inspect.getsource` plus AST source
slicing, wrapping each default in a ``DefaultValue`` shim whose
``__repr__`` returns the literal source text. It explicitly bails
out on synthetic ``__init__`` signatures (dataclass / attrs /
NamedTuple) — see
``sphinx/ext/autodoc/_dynamic/_preserve_defaults.py:107-110``.

This module fills that gap.
:func:`update_synthetic_defvalues` is connected to the
``autodoc-before-process-signature`` event and runs after Sphinx's
own ``update_defvalue``. For each parameter whose default is still a
raw Python object (not a ``DefaultValue`` shim), it walks
:func:`dataclasses.fields` on the parent class, runs a resolver
chain over the field's ``default`` / ``default_factory``, and
replaces ``Parameter.default`` with ``DefaultValue(<chosen text>)``.
After that, all downstream stringifiers emit the chosen text
verbatim, the directive arglist parses, and rendering is clean.

The resolver chain is the seam for future extension. The built-in
catalog is seeded by the empirical inventory in
``notes/defaults-discovery-d1.md`` (libtmux's 90 ``<factory>``
occurrences from dataclass ``field(default_factory=…)``).
"""

from __future__ import annotations

import dataclasses
import inspect
import logging
import sys
import typing as t

from sphinx.util.inspect import DefaultValue

from sphinx_autodoc_typehints_gp._resolvers import (
    DataclassFactoryRepr,
    ResolveContext,
    Resolver,
    run_chain,
)

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)

_DEFAULT_RESOLVERS: tuple[Resolver, ...] = (DataclassFactoryRepr(),)


def _walk_to_dataclass(obj: t.Any) -> type | None:
    """Find the dataclass that owns *obj*'s synthetic ``__init__``.

    Returns ``None`` if *obj* is not a synthetic dataclass init.
    Handles both the ``isinstance(obj, type)`` case (autodoc passes
    the class) and the bound-/unbound-method case (autodoc passes
    ``Cls.__init__``).

    Examples
    --------
    >>> import dataclasses
    >>> @dataclasses.dataclass
    ... class _ExampleDC:
    ...     x: int = 0
    >>> _walk_to_dataclass(_ExampleDC) is _ExampleDC
    True
    >>> class _Plain:
    ...     pass
    >>> _walk_to_dataclass(_Plain) is None
    True
    >>> _walk_to_dataclass(42) is None
    True
    """
    if isinstance(obj, type) and dataclasses.is_dataclass(obj):
        return obj
    qualname = getattr(obj, "__qualname__", "")
    if not qualname.endswith(".__init__"):
        return None
    module_name = getattr(obj, "__module__", None)
    if not module_name:
        return None
    module = sys.modules.get(module_name)
    if module is None:
        return None
    parent: t.Any = module
    for part in qualname.split(".")[:-1]:
        parent = getattr(parent, part, None)
        if parent is None:
            return None
    if isinstance(parent, type) and dataclasses.is_dataclass(parent):
        return parent
    return None


def update_synthetic_defvalues(
    app: Sphinx,
    obj: t.Any,
    bound_method: bool,
) -> None:
    """Fill defaults for synthetic dataclass ``__init__`` signatures.

    Connected to ``autodoc-before-process-signature``. Mutates
    ``obj.__signature__`` so that downstream stringifiers emit the
    resolver-chosen text. No-op when:

    - the config flag ``gp_typehints_curate_param_defaults`` is
      ``False``;
    - *obj* is not (and is not the ``__init__`` of) a dataclass;
    - every parameter's default is already a ``DefaultValue`` shim
      (Sphinx's ``update_defvalue`` already handled them);
    - no resolver returns a non-``None`` result.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application instance.
    obj : Any
        The function or class being introspected.
    bound_method : bool
        Whether *obj* is a bound method (Sphinx event arg).

    Examples
    --------
    >>> update_synthetic_defvalues  # doctest: +ELLIPSIS
    <function update_synthetic_defvalues at 0x...>
    """
    if not getattr(app.config, "gp_typehints_curate_param_defaults", True):
        return
    parent = _walk_to_dataclass(obj)
    if parent is None:
        return
    try:
        sig = inspect.signature(obj)
    except (TypeError, ValueError):
        return

    fields_by_name = {f.name: f for f in dataclasses.fields(parent)}
    new_parameters: list[inspect.Parameter] = []
    changed = False
    for param in sig.parameters.values():
        if isinstance(param.default, DefaultValue):
            new_parameters.append(param)
            continue
        if param.default is inspect.Parameter.empty:
            new_parameters.append(param)
            continue
        field = fields_by_name.get(param.name)
        if field is None:
            new_parameters.append(param)
            continue
        if field.default_factory is dataclasses.MISSING:
            new_parameters.append(param)
            continue
        ctx = ResolveContext(
            value=field.default_factory,
            kind="param",
            qualname=getattr(obj, "__qualname__", "<unknown>"),
            param_name=param.name,
            default_repr="<factory>",
        )
        text = run_chain(ctx, _DEFAULT_RESOLVERS)
        if text is None:
            new_parameters.append(param)
            continue
        new_parameters.append(param.replace(default=DefaultValue(text)))
        changed = True

    if not changed:
        return
    new_sig = sig.replace(parameters=new_parameters)
    try:
        obj.__signature__ = new_sig
    except (AttributeError, TypeError):
        try:
            obj.__dict__["__signature__"] = new_sig
        except (AttributeError, TypeError):
            logger.debug("failed to set __signature__ on %r", obj)
