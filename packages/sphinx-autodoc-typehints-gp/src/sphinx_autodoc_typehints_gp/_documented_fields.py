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
import itertools
import re
import sys
import typing as t
import weakref

from sphinx.ext.autodoc import ALL

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.ext.autodoc._legacy_class_based._directive_options import (  # type: ignore[import-not-found]
        Options,
    )

_ATTRIBUTE_DIRECTIVE = ".. attribute:: "
_CLASS_LIKE_AUTODOC_TYPES = frozenset({"class", "exception"})
_UNSET = object()
_CLASS_VAR_RE = re.compile(r"\s*(?:\w+\.)*ClassVar\b")


class _ProcessedFields(t.NamedTuple):
    """Fields emitted for the class whose members are being filtered.

    Attributes
    ----------
    options : object
        Exact options object shared by one class documenter invocation.
    owner : type
        Exact class whose processed docstring emitted the fields.
    names : frozenset[str]
        Attribute directive names in that processed docstring.
    """

    options: object
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


def _add_attribute_no_index(lines: list[str]) -> None:
    """Apply ``:no-index:`` to emitted attribute directives.

    Parameters
    ----------
    lines : list[str]
        Final processed docstring lines, modified in place.

    Examples
    --------
    >>> body = [".. attribute:: value", "", "   Description."]
    >>> _add_attribute_no_index(body)
    >>> body
    ['.. attribute:: value', '   :no-index:', '', '   Description.']

    >>> existing = [".. attribute:: value", "    :noindex:", ""]
    >>> _add_attribute_no_index(existing)
    >>> existing
    ['.. attribute:: value', '    :noindex:', '']
    """
    updated: list[str] = []
    for index, line in enumerate(lines):
        updated.append(line)
        if not line.startswith(_ATTRIBUTE_DIRECTIVE):
            continue
        option_lines = itertools.takewhile(
            lambda candidate: (
                candidate[:1].isspace() and candidate.lstrip().startswith(":")
            ),
            lines[index + 1 :],
        )
        if not any(
            option.strip() in {":no-index:", ":noindex:"} for option in option_lines
        ):
            updated.append("   :no-index:")
    lines[:] = updated


def _coalesce_attribute_directives(
    lines: list[str],
    documented: t.Iterable[str] = (),
    excluded: t.Iterable[str] = (),
) -> list[str]:
    """Keep the first complete directive block for each attribute name.

    Parameters
    ----------
    lines : list[str]
        Fully processed class and initializer docstring lines.
    documented : typing.Iterable[str]
        Attribute names emitted by an earlier docstring from the same
        documenter invocation.
    excluded : typing.Iterable[str]
        Attribute names whose concrete members are authoritative.

    Returns
    -------
    list[str]
        Lines with later directive blocks for the same attribute removed.

    Examples
    --------
    >>> _coalesce_attribute_directives(
    ...     [
    ...         ".. attribute:: value",
    ...         "",
    ...         "   Class description.",
    ...         "Initializer.",
    ...         ".. attribute:: value",
    ...         "",
    ...         "   Initializer copy.",
    ...     ]
    ... )
    ['.. attribute:: value', '', '   Class description.', 'Initializer.']

    >>> _coalesce_attribute_directives(
    ...     [".. attribute:: value", "", "   Stale description."],
    ...     excluded={"value"},
    ... )
    []
    """
    seen = set(documented)
    excluded_names = set(excluded)
    coalesced: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.startswith(_ATTRIBUTE_DIRECTIVE):
            coalesced.append(line)
            index += 1
            continue

        name = line[len(_ATTRIBUTE_DIRECTIVE) :].strip()
        block_end = index + 1
        while block_end < len(lines):
            candidate = lines[block_end]
            if candidate and not candidate[:1].isspace():
                break
            block_end += 1

        if name not in seen and name not in excluded_names:
            seen.add(name)
            coalesced.extend(lines[index:block_end])
        index = block_end
    return coalesced


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
        namespace = vars(klass)
    except TypeError:
        return {}
    annotations = namespace.get("__annotations__")
    if not isinstance(annotations, dict):
        annotations = namespace.get("__annotations_cache__")
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
    annotations = _declared_annotations(klass)
    if name in annotations and _is_class_var(annotations[name]):
        return False

    mro = getattr(klass, "__mro__", (klass,))
    exposed = inspect.getattr_static(klass, name, _UNSET)
    member_owner = next((base for base in mro if name in vars(base)), None)
    is_non_field_member = (
        isinstance(exposed, property | staticmethod | classmethod | type)
        or inspect.isroutine(exposed)
        or inspect.ismethoddescriptor(exposed)
    )

    fields = getattr(klass, "_fields", None)
    if issubclass(klass, tuple) and isinstance(fields, tuple) and name in fields:
        field_owner = None
        for base in mro:
            base_fields = vars(base).get("_fields")
            if (
                isinstance(base_fields, tuple)
                and name in base_fields
                and name in _own_annotations(base)
            ):
                field_owner = base
                break
        return field_owner is member_owner or not is_non_field_member

    if dataclasses.is_dataclass(klass):
        if name not in {field.name for field in dataclasses.fields(klass)}:
            return False
        field_owner = None
        for base in mro:
            base_fields = vars(base).get("__dataclass_fields__")
            if (
                isinstance(base_fields, dict)
                and name in base_fields
                and name in _own_annotations(base)
            ):
                field_owner = base
                break
        return field_owner is member_owner or not is_non_field_member

    if t.is_typeddict(klass):
        return name in (
            getattr(klass, "__required_keys__", frozenset())
            | getattr(klass, "__optional_keys__", frozenset())
        )

    if name not in annotations:
        return False
    return not is_non_field_member


def _is_concrete_non_field_member(klass: type, name: str) -> bool:
    """Return whether a concrete member should own its documentation.

    Properties, methods, nested classes, and ``ClassVar`` values carry
    signatures or values that an ``Attributes`` entry cannot preserve.
    Callable and class-valued dataclass defaults remain fields when
    :func:`_is_declared_field` confirms their metadata lineage.

    Parameters
    ----------
    klass : type
        Class being documented.
    name : str
        Member name under consideration.

    Returns
    -------
    bool
        Whether autodoc's concrete member description is authoritative.

    Examples
    --------
    >>> class Service:
    ...     @property
    ...     def status(self) -> str:
    ...         '''Return the service status.'''
    ...         return "ready"
    >>> _is_concrete_non_field_member(Service, "status")
    True

    >>> @dataclasses.dataclass
    ... class Converter:
    ...     callback: t.Callable[[str], str] = str.upper
    >>> _is_concrete_non_field_member(Converter, "callback")
    False
    """
    annotations = _declared_annotations(klass)
    if name in annotations and _is_class_var(annotations[name]):
        return True

    exposed = inspect.getattr_static(klass, name, _UNSET)
    looks_concrete = (
        isinstance(exposed, property | staticmethod | classmethod | type)
        or inspect.isroutine(exposed)
        or inspect.ismethoddescriptor(exposed)
    )
    return looks_concrete and not _is_declared_field(klass, name)


def _concrete_member_will_render(
    klass: type,
    name: str,
    options: Options,
) -> bool:
    """Return whether autodoc will render a concrete non-field member.

    Parameters
    ----------
    klass : type
        Class being documented.
    name : str
        Concrete member name under consideration.
    options : Options
        Options controlling member selection for the class documenter.

    Returns
    -------
    bool
        Whether the concrete member can replace its ``Attributes`` entry.

    Examples
    --------
    >>> class Selected:
    ...     members = ALL
    ...     exclude_members: set[str] = set()
    ...     private_members = None
    ...     special_members = None
    ...     undoc_members = None
    >>> class Service:
    ...     @property
    ...     def status(self) -> str:
    ...         '''Return the service status.'''
    ...         return "ready"
    >>> _concrete_member_will_render(
    ...     Service,
    ...     "status",
    ...     t.cast("Options", Selected()),
    ... )
    True

    >>> Selected.exclude_members = {"status"}
    >>> _concrete_member_will_render(
    ...     Service,
    ...     "status",
    ...     t.cast("Options", Selected()),
    ... )
    False
    """
    if not _is_concrete_non_field_member(klass, name):
        return False

    members = options.members
    if members is None or (members is not ALL and name not in members):
        return False
    excluded = options.exclude_members
    if isinstance(excluded, set) and name in excluded:
        return False

    if members is ALL:
        if name.startswith("__") and name.endswith("__"):
            special = options.special_members
            if special is None or (special is not ALL and name not in special):
                return False
        elif name.startswith("_"):
            private = options.private_members
            if private is None or (private is not ALL and name not in private):
                return False

    annotations = _declared_annotations(klass)
    if name in annotations and _is_class_var(annotations[name]):
        return bool(options.undoc_members)
    if options.undoc_members:
        return True
    exposed = inspect.getattr_static(klass, name, _UNSET)
    return inspect.getdoc(exposed) is not None


def record_documented_fields(
    app: Sphinx,
    what: str,
    name: str,
    obj: t.Any,
    options: Options,
    lines: list[str],
) -> None:
    """Record fields emitted by final processed class docstrings.

    Installed after extension initialization as the final
    ``autodoc-process-docstring`` listener. The application-local record
    carries the exact owner and final emitted attribute names into
    ``autodoc-skip-member``.

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
    if what not in _CLASS_LIKE_AUTODOC_TYPES or not isinstance(obj, type):
        if options.no_index or options.noindex:
            _add_attribute_no_index(lines)
        return
    previous = _PROCESSED_FIELDS.get(app)
    documented = (
        previous.names
        if previous is not None
        and previous.options is options
        and previous.owner is obj
        else frozenset()
    )
    concrete_members = {
        field_name
        for field_name in _attribute_directive_names(lines)
        if _concrete_member_will_render(obj, field_name, options)
    }
    lines[:] = _coalesce_attribute_directives(
        lines,
        documented,
        concrete_members,
    )
    if options.no_index or options.noindex:
        _add_attribute_no_index(lines)
    names = _attribute_directive_names(lines) | documented
    _PROCESSED_FIELDS[app] = _ProcessedFields(
        options=options,
        owner=obj,
        names=names,
    )


def _prepare_documented_fields(app: Sphinx) -> None:
    """Install field finalization after every extension has initialized.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance being built.

    Examples
    --------
    >>> callable(_prepare_documented_fields)
    True
    """
    _PROCESSED_FIELDS.pop(app, None)
    app.connect(
        "autodoc-process-docstring",
        record_documented_fields,
        priority=sys.maxsize,
    )


def _clear_documented_fields(
    app: Sphinx,
    what: str,
    name: str,
    obj: t.Any,
    options: Options,
    args: str | None,
    retann: str | None,
) -> None:
    """Clear a prior owner when a class documenter starts.

    ``autodoc-process-signature`` runs before documenter content even when a
    custom ``get_doc()`` returns ``None`` and suppresses the docstring event.
    Clearing at that boundary prevents a nested documenter reusing its
    parent's options from inheriting the parent's field record.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance being built.
    what : str
        Type of object whose signature is being processed.
    name : str
        Fully qualified autodoc name.
    obj : typing.Any
        Object whose signature is being processed.
    options : Options
        Options shared by the current autodoc directive.
    args : str | None
        Rendered positional signature.
    retann : str | None
        Rendered return annotation.

    Examples
    --------
    >>> _clear_documented_fields  # doctest: +ELLIPSIS
    <function _clear_documented_fields at 0x...>
    """
    if what in _CLASS_LIKE_AUTODOC_TYPES and isinstance(obj, type):
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
    if skip or what not in _CLASS_LIKE_AUTODOC_TYPES:
        return None

    processed = _PROCESSED_FIELDS.get(app)
    if processed is None or processed.options is not options:
        return None

    if not _is_declared_field(processed.owner, name):
        return None
    if name not in processed.names:
        return None
    return True


def register(app: Sphinx) -> None:
    """Register late field finalization and member filtering.

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
    app.connect(
        "autodoc-process-signature",
        _clear_documented_fields,
        priority=0,
    )
    app.connect(
        "builder-inited",
        _prepare_documented_fields,
        priority=sys.maxsize,
    )
