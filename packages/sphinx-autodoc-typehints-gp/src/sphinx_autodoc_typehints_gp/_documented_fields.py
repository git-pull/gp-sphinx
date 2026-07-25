"""Drop autodoc field stubs a NumPy ``Attributes`` section already describes.

A class that declares fields hands autodoc one member per field.
:class:`typing.NamedTuple` compiles each into a ``_tuplegetter`` descriptor
whose ``__doc__`` is the boilerplate ``"Alias for field number N"``; a
dataclass field or a :class:`typing.TypedDict` key arrives as a bare
annotation; a field of a ``slots=True`` dataclass arrives as autodoc's slot
sentinel. Autodoc emits a ``py:attribute`` for all of them — the boilerplate
counts as a real docstring, and ``undoc-members`` covers the rest.

When the owning class docstring carries a NumPy ``Attributes`` section naming
that field, :mod:`sphinx_autodoc_typehints_gp._numpy_docstring` has already
emitted an ``.. attribute::`` directive for the same dotted name. Two
descriptions of one object reach the Python domain, and it warns:

.. code-block:: text

   WARNING: duplicate object description of pkg.mod.Point.x, other instance
   in index, use :no-index: for one of them

Because this package owns the ``.. attribute::`` directive that wins, it also
owns suppressing the loser. :func:`skip_documented_fields` hooks
``autodoc-skip-member`` and drops autodoc's copy — and nothing else. The
member names it treats as already described are recorded from the exact
processed class docstring that emitted the competing directives, so another
docstring processor and a field the ``Attributes`` section leaves out both
remain authoritative.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import re
import typing as t
import weakref

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.ext.autodoc._legacy_class_based._directive_options import (  # type: ignore[import-not-found]
        Options,
    )

_ATTRIBUTE_DIRECTIVE = ".. attribute:: "
_UNSET = object()
_CLASS_VAR_RE = re.compile(r"\s*(?:\w+\.)*ClassVar\b")


class _ProcessedFields(t.NamedTuple):
    """Fields emitted for the class whose members are being filtered.

    Attributes
    ----------
    owner : type
        Exact class whose processed docstring emitted the fields.
    names : frozenset[str]
        Attribute directive names in that processed docstring.
    """

    owner: type
    names: frozenset[str]


_PROCESSED_FIELDS: weakref.WeakKeyDictionary[Sphinx, _ProcessedFields] = (
    weakref.WeakKeyDictionary()
)


def _attribute_directive_names(lines: t.Iterable[str]) -> frozenset[str]:
    """Return attribute names emitted in processed docstring *lines*.

    Parameters
    ----------
    lines : typing.Iterable[str]
        Final processed autodoc docstring lines.

    Returns
    -------
    frozenset[str]
        Names carried by ``.. attribute::`` directives.

    Examples
    --------
    >>> _attribute_directive_names([".. attribute:: x", "", "summary"])
    frozenset({'x'})
    """
    return frozenset(
        line[len(_ATTRIBUTE_DIRECTIVE) :].strip()
        for line in lines
        if line.startswith(_ATTRIBUTE_DIRECTIVE)
    )


def _own_annotations(klass: type) -> dict[str, t.Any]:
    """Return the annotations declared in *klass*'s own body.

    Read the class namespace rather than resolving annotations. On Python
    3.14, accessing ``klass.__annotations__`` can execute a deferred
    annotation; a mapping not yet materialized therefore counts as declaring
    nothing. Named tuples, dataclasses, and typed dictionaries are classified
    from their own field metadata before this conservative fallback is used.

    Parameters
    ----------
    klass : type
        Class to read annotations from.

    Returns
    -------
    dict[str, t.Any]
        Annotations the class body declares, left unresolved.

    Examples
    --------
    >>> class Point:
    ...     x: int
    >>> _own_annotations(Point)
    {'x': 'int'}

    >>> _own_annotations(object)
    {}
    """
    try:
        annotations = vars(klass).get("__annotations__")
    except TypeError:
        return {}
    return dict(annotations) if isinstance(annotations, dict) else {}


def _declared_annotations(klass: type) -> dict[str, t.Any]:
    """Return the annotations *klass* declares, inherited ones included.

    Walking the MRO picks up a dataclass field a base class declares. A
    :class:`typing.TypedDict` keeps no base ``TypedDict`` in its MRO but
    merges inherited keys into its own annotations, so those arrive too.

    Parameters
    ----------
    klass : type
        Class whose declared fields are being resolved.

    Returns
    -------
    dict[str, t.Any]
        Annotations by name, the most derived declaration winning.

    Examples
    --------
    >>> class Base:
    ...     x: int
    >>> class Child(Base):
    ...     y: str
    >>> sorted(_declared_annotations(Child))
    ['x', 'y']
    """
    collected: dict[str, t.Any] = {}
    for base in reversed(getattr(klass, "__mro__", (klass,))):
        collected.update(_own_annotations(base))
    return collected


def _is_class_var(annotation: t.Any) -> bool:
    """Return whether *annotation* marks a class-level constant.

    Handles both the resolved form and the string a module using
    ``from __future__ import annotations`` leaves behind.

    Parameters
    ----------
    annotation : t.Any
        An unresolved annotation value.

    Returns
    -------
    bool
        Whether the annotation is a :data:`typing.ClassVar`.

    Examples
    --------
    >>> _is_class_var(t.ClassVar[int])
    True

    >>> _is_class_var("t.ClassVar[int]")
    True

    >>> _is_class_var(int)
    False
    """
    while isinstance(annotation, str):
        try:
            unquoted = ast.literal_eval(annotation)
        except (SyntaxError, ValueError):
            break
        if not isinstance(unquoted, str) or unquoted == annotation:
            break
        annotation = unquoted
    if isinstance(annotation, str):
        return _CLASS_VAR_RE.match(annotation) is not None
    return annotation is t.ClassVar or t.get_origin(annotation) is t.ClassVar


def _is_declared_field(klass: type, name: str) -> bool:
    """Return whether *klass* declares *name* as one of its fields.

    A :class:`typing.NamedTuple` lists its fields in ``_fields``. Every other
    shape — dataclass field, :class:`typing.TypedDict` key, annotated
    instance attribute — declares them by annotation. A ``ClassVar``
    annotates a class-level constant rather than a field, and a name the
    class exposes as a :class:`property` belongs to that property, so neither
    counts.

    Parameters
    ----------
    klass : type
        Class being documented.
    name : str
        Member name under consideration.

    Returns
    -------
    bool
        Whether the member is a field the class declares.

    Examples
    --------
    >>> import dataclasses
    >>> @dataclasses.dataclass
    ... class Point:
    ...     x: int
    ...     origin: t.ClassVar[int] = 0
    ...
    ...     @property
    ...     def magnitude(self) -> int:
    ...         return self.x
    >>> _is_declared_field(Point, "x")
    True

    >>> _is_declared_field(Point, "origin")
    False

    >>> _is_declared_field(Point, "magnitude")
    False
    """
    fields = getattr(klass, "_fields", None)
    if isinstance(fields, tuple) and name in fields:
        return True

    if dataclasses.is_dataclass(klass):
        return name in {field.name for field in dataclasses.fields(klass)}

    if t.is_typeddict(klass):
        return name in (
            getattr(klass, "__required_keys__", frozenset())
            | getattr(klass, "__optional_keys__", frozenset())
        )

    annotations = _declared_annotations(klass)
    if name not in annotations or _is_class_var(annotations[name]):
        return False
    exposed = inspect.getattr_static(klass, name, _UNSET)
    return not (
        isinstance(exposed, property | staticmethod | classmethod | type)
        or inspect.isroutine(exposed)
        or inspect.ismethoddescriptor(exposed)
    )


def record_documented_fields(
    app: Sphinx,
    what: str,
    name: str,
    obj: t.Any,
    options: Options,
    lines: list[str],
) -> None:
    """Record fields emitted by an actual processed class docstring.

    Connected late to ``autodoc-process-docstring``. Sphinx processes a
    class's docstring immediately before filtering that class's members, so
    the application-local record carries the exact owner and final emitted
    attribute names into ``autodoc-skip-member``.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance being built.
    what : str
        Type of object whose docstring was processed.
    name : str
        Fully qualified autodoc name.
    obj : typing.Any
        Object whose docstring was processed.
    options : Options
        Options given to the autodoc directive.
    lines : list[str]
        Processed docstring lines at this event priority.

    Examples
    --------
    >>> record_documented_fields  # doctest: +ELLIPSIS
    <function record_documented_fields at 0x...>
    """
    if what != "class" or not isinstance(obj, type):
        return
    _PROCESSED_FIELDS[app] = _ProcessedFields(
        owner=obj,
        names=_attribute_directive_names(lines),
    )


def _clear_processed_fields(app: Sphinx) -> None:
    """Clear the application's processed field record before a build.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance being built.

    Examples
    --------
    >>> callable(_clear_processed_fields)
    True
    """
    _PROCESSED_FIELDS.pop(app, None)


def skip_documented_fields(
    app: Sphinx,
    what: str,
    name: str,
    obj: t.Any,
    skip: bool,
    options: Options,
) -> bool | None:
    """Skip a field whose ``Attributes`` entry autodoc would duplicate.

    Connected to ``autodoc-skip-member``. Returns ``True`` only when every
    one of these holds:

    - autodoc is not already skipping the member;
    - an exact class and processed docstring were recorded;
    - that class declares *name* as a field, through ``_fields`` or through
      an annotation on itself or a base;
    - the processed class docstring emitted an attribute directive for
      *name*.

    Returns ``None`` in every other case, leaving the member to autodoc and
    to any other handler.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application instance.
    what : str
        The object type of the documenter doing the filtering.
    name : str
        The member name under consideration.
    obj : t.Any
        The member itself.
    skip : bool
        Whether autodoc would skip the member on its own.
    options : Options
        The options given to the autodoc directive.

    Returns
    -------
    bool | None
        ``True`` to drop a duplicate field, ``None`` to abstain.

    Examples
    --------
    >>> skip_documented_fields  # doctest: +ELLIPSIS
    <function skip_documented_fields at 0x...>
    """
    if skip or what != "class":
        return None

    processed = _PROCESSED_FIELDS.get(app)
    if processed is None:
        return None

    if not _is_declared_field(processed.owner, name):
        return None
    if name not in processed.names:
        return None
    return True


def register(app: Sphinx) -> None:
    """Connect the duplicate-field skip handler to the Sphinx app.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application instance.

    Examples
    --------
    >>> register  # doctest: +ELLIPSIS
    <function register at 0x...>
    """
    app.connect("builder-inited", _clear_processed_fields)
    app.connect(
        "autodoc-process-docstring",
        record_documented_fields,
        priority=999,
    )
    app.connect("autodoc-skip-member", skip_documented_fields)
