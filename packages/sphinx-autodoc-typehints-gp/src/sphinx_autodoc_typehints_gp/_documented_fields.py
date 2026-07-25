"""Drop autodoc field stubs a NumPy ``Attributes`` section already describes.

A class that declares fields hands autodoc one member per field.
:class:`typing.NamedTuple` compiles each into a ``_tuplegetter`` descriptor
whose ``__doc__`` is the boilerplate ``"Alias for field number N"``; a
dataclass field or a :class:`typing.TypedDict` key arrives as a bare
annotation. Autodoc emits a ``py:attribute`` for all of them — the
boilerplate counts as a real docstring, and ``undoc-members`` covers the
rest.

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
member names it treats as already described are read back out of the very
preprocessor that emitted the competing directives, so the two cannot
disagree, and a field the ``Attributes`` section leaves out still renders.
"""

from __future__ import annotations

import inspect
import re
import sys
import typing as t

from sphinx_autodoc_typehints_gp._numpy_docstring import process_numpy_docstring

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.ext.autodoc._legacy_class_based._directive_options import (  # type: ignore[import-not-found]
        Options,
    )

_ATTRIBUTE_DIRECTIVE = ".. attribute:: "
_UNSET = object()
_CLASS_VAR_RE = re.compile(r"\s*(?:\w+\.)*ClassVar\b")


def _numpy_attribute_names(doc: str | None) -> frozenset[str]:
    """Return the member names an ``Attributes`` section of *doc* describes.

    Runs the same preprocessor that emits the competing ``.. attribute::``
    directives and collects the names it produced, so the skip decision and
    the rendered directives can never disagree about what is documented.

    Parameters
    ----------
    doc : str | None
        A class docstring, or ``None``.

    Returns
    -------
    frozenset[str]
        Names the docstring emits an ``.. attribute::`` directive for.

    Examples
    --------
    >>> _numpy_attribute_names('''A point.
    ...
    ...     Attributes
    ...     ----------
    ...     x : int
    ...         Horizontal offset.
    ...     ''')
    frozenset({'x'})

    >>> _numpy_attribute_names("Summary only.")
    frozenset()

    >>> _numpy_attribute_names(None)
    frozenset()
    """
    if not doc:
        return frozenset()
    lines = process_numpy_docstring(inspect.cleandoc(doc).splitlines())
    return frozenset(
        line[len(_ATTRIBUTE_DIRECTIVE) :].strip()
        for line in lines
        if line.startswith(_ATTRIBUTE_DIRECTIVE)
    )


def _own_annotations(klass: type) -> dict[str, t.Any]:
    """Return the annotations declared in *klass*'s own body.

    Read straight off the class rather than through
    :func:`typing.get_type_hints`, which resolves a string annotation with
    :func:`eval` and can import a module the build never asked for. Only
    ``ClassVar`` is ever read back out of the values, so leaving them
    unresolved costs nothing. A class that cannot carry annotations at all —
    :class:`object`, :class:`tuple`, :class:`dict` — and annotations that
    fail to materialize both count as declaring nothing.

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
        annotations = klass.__annotations__
    except Exception:
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

    annotations = _declared_annotations(klass)
    if name not in annotations or _is_class_var(annotations[name]):
        return False
    return not isinstance(inspect.getattr_static(klass, name, None), property)


def _documented_class(app: Sphinx) -> type | None:
    """Return the class whose members autodoc is currently filtering.

    ``autodoc-skip-member`` is handed the member but not its owner.
    ``Documenter.document_members`` records the module name and the head of
    the object path on the current document before filtering starts, so the
    owner can be walked back out of :data:`sys.modules`.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application instance.

    Returns
    -------
    type | None
        The class being documented, or ``None`` when no class is in scope or
        the recorded path no longer resolves to one.

    Examples
    --------
    >>> _documented_class  # doctest: +ELLIPSIS
    <function _documented_class at 0x...>
    """
    current = app.env.current_document
    if not current.autodoc_class:
        return None
    owner: t.Any = sys.modules.get(current.autodoc_module)
    if owner is None:
        return None
    for part in current.autodoc_class.split("."):
        owner = getattr(owner, part, None)
        if owner is None:
            return None
    return owner if isinstance(owner, type) else None


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
    - a class documenter is running and its class still resolves;
    - that class declares *name* as a field, through ``_fields`` or through
      an annotation on itself or a base;
    - *obj* is the attribute the class exposes under *name*, where the class
      exposes one at all — a :class:`typing.TypedDict` key and a dataclass
      field without a default leave nothing on the class to compare against;
    - the class docstring's ``Attributes`` section describes *name*.

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

    owner = _documented_class(app)
    if owner is None:
        return None

    if not _is_declared_field(owner, name):
        return None

    exposed = inspect.getattr_static(owner, name, _UNSET)
    if exposed is not _UNSET and exposed is not obj:
        return None
    if name not in _numpy_attribute_names(owner.__doc__):
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
    app.connect("autodoc-skip-member", skip_documented_fields)
