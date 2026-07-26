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

Because this package owns the ``.. attribute::`` directive, it also owns
choosing the authoritative description. :func:`skip_documented_fields` drops
autodoc's copy for declared fields. Properties, methods, and class variables
instead keep their field directive marked until Sphinx finishes rendering
members; a wrapper around the final registered documenter removes the
fallback only when a concrete directive was actually emitted. The member
names come from the exact processed class docstring, so other docstring and
skip handlers remain authoritative.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import itertools
import re
import sys
import textwrap
import typing as t
import weakref

from docutils.statemachine import StringList
from sphinx.ext.autodoc import Documenter, PropertyDocumenter

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.ext.autodoc._legacy_class_based._directive_options import (  # type: ignore[import-not-found]
        Options,
    )

_ATTRIBUTE_DIRECTIVE = ".. attribute:: "
_FIELD_MARKER = ".. gp-sphinx-documented-field: "
_CLASS_LIKE_AUTODOC_TYPES = frozenset({"class", "exception"})
_UNSET = object()
_CLASS_VAR_RE = re.compile(r"\s*(?:\w+\.)*ClassVar\b")
_OBJECT_DIRECTIVE_RE = re.compile(r"^\s*\.\. (?:\w+:)?[\w-]+::\s+([^\s(=:]+)")
_RENDERED_FIELD_RE = re.compile(r"^\s*:(?:type|value):(?:\s|$)")


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
    instance attribute, or ordinary runtime data attribute — declares data
    rather than behavior. A ``ClassVar`` annotates a class-level constant
    rather than a field, and a name the class exposes as a
    :class:`property` belongs to that property, so neither counts.

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
        return exposed is not _UNSET and not is_non_field_member
    return not is_non_field_member


def _mark_attribute_directives(lines: list[str], owner: str) -> None:
    """Mark field directives until autodoc finishes rendering members.

    Parameters
    ----------
    lines : list[str]
        Final processed class docstring lines, modified in place.
    owner : str
        Fully qualified name of the class documenter.

    Examples
    --------
    >>> body = ["Summary.", ".. attribute:: value", "", "   Details."]
    >>> _mark_attribute_directives(body, "demo.Item")
    >>> body[1:3]
    ['.. gp-sphinx-documented-field: demo.Item value', '.. attribute:: value']
    """
    marked: list[str] = []
    for line in lines:
        if line.startswith(_ATTRIBUTE_DIRECTIVE):
            field_name = line[len(_ATTRIBUTE_DIRECTIVE) :].strip()
            marked.append(f"{_FIELD_MARKER}{owner} {field_name}")
        marked.append(line)
    lines[:] = marked


def _rendered_field_names(
    lines: t.Iterable[str],
    object_path: t.Iterable[str],
    candidates: t.Iterable[str],
    indent: str,
) -> frozenset[str]:
    """Return marked fields whose member directives autodoc emitted.

    Parameters
    ----------
    lines : typing.Iterable[str]
        Generated member output added after the class docstring.
    object_path : typing.Iterable[str]
        Class path used in generated Python directives.
    candidates : typing.Iterable[str]
        Marked field names under consideration.
    indent : str
        Indentation of direct member directives.

    Returns
    -------
    frozenset[str]
        Candidate names with a rendered direct-member directive.

    Examples
    --------
    >>> _rendered_field_names(
    ...     [
    ...         "   .. py:property:: Item.value",
    ...         "      .. py:attribute:: Item.nested",
    ...     ],
    ...     ["Item"],
    ...     {"nested", "value"},
    ...     "   ",
    ... )
    frozenset({'value'})
    """
    candidate_names = set(candidates)
    object_prefix = f"{'.'.join(object_path)}."
    rendered: set[str] = set()
    for line in lines:
        if not line.startswith(f"{indent}.. "):
            continue
        match = _OBJECT_DIRECTIVE_RE.match(line)
        if match is None:
            continue
        target = match.group(1)
        if target.startswith(object_prefix):
            candidate = target[len(object_prefix) :]
            if candidate in candidate_names:
                rendered.add(candidate)
    return frozenset(rendered)


def _resolve_marked_fields(
    lines: StringList,
    owner: str,
    rendered: t.Iterable[str],
) -> None:
    """Remove markers and field blocks replaced by rendered members.

    Parameters
    ----------
    lines : docutils.statemachine.StringList
        Generated autodoc reStructuredText, modified in place.
    owner : str
        Fully qualified name of the current class documenter.
    rendered : typing.Iterable[str]
        Fields whose concrete member directives were emitted.

    Examples
    --------
    >>> body = StringList(
    ...     [
    ...         "   .. gp-sphinx-documented-field: demo.Item value",
    ...         "   .. attribute:: value",
    ...         "",
    ...         "      Details.",
    ...         "   .. py:property:: Item.value",
    ...     ],
    ...     source="demo",
    ... )
    >>> _resolve_marked_fields(body, "demo.Item", {"value"})
    >>> body.data
    ['   .. py:property:: Item.value']
    """
    rendered_names = set(rendered)
    marker_prefix = f"{_FIELD_MARKER}{owner} "
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.lstrip()
        if not stripped.startswith(marker_prefix):
            index += 1
            continue

        field_name = stripped[len(marker_prefix) :].strip()
        marker_indent = line[: len(line) - len(stripped)]
        directive_index = index + 1
        expected = f"{marker_indent}{_ATTRIBUTE_DIRECTIVE}{field_name}"
        if (
            field_name not in rendered_names
            or directive_index >= len(lines)
            or lines[directive_index] != expected
        ):
            del lines[index]
            continue

        block_end = directive_index + 1
        while block_end < len(lines):
            candidate = lines[block_end]
            candidate_stripped = candidate.lstrip()
            candidate_indent = len(candidate) - len(candidate_stripped)
            if candidate_stripped and candidate_indent <= len(marker_indent):
                break
            block_end += 1
        for block_index in reversed(range(index, block_end)):
            del lines[block_index]


def _strip_rendered_fields(body: list[str]) -> list[str]:
    """Drop the ``:type:`` and ``:value:`` entries and surrounding blanks.

    Parameters
    ----------
    body : list[str]
        Description lines dedented to column zero.

    Returns
    -------
    list[str]
        The description alone.

    Examples
    --------
    >>> _strip_rendered_fields(["Horizontal offset.", "", ":type: int"])
    ['Horizontal offset.']

    >>> _strip_rendered_fields([":type: int", "   wrapped", "Offset."])
    ['Offset.']
    """
    kept: list[str] = []
    dropping = False
    for line in body:
        if _RENDERED_FIELD_RE.match(line) is not None:
            dropping = True
            continue
        if dropping:
            if not line.strip() or line[:1].isspace():
                continue
            dropping = False
        kept.append(line)
    while kept and not kept[0].strip():
        kept.pop(0)
    while kept and not kept[-1].strip():
        kept.pop()
    return kept


def _field_doc_bodies(
    lines: t.Iterable[str],
    marker_prefix: str,
) -> dict[str, list[str]]:
    """Return the prose each marked field directive carries.

    The type and value are dropped: the member's own directive renders
    both from the annotation itself, which is what a class variable's
    entry cannot express.

    Parameters
    ----------
    lines : typing.Iterable[str]
        Generated reStructuredText holding marked field directives.
    marker_prefix : str
        Marker prefix identifying the current class documenter.

    Returns
    -------
    dict[str, list[str]]
        Description lines by field name, dedented to column zero.

    Examples
    --------
    >>> _field_doc_bodies(
    ...     [
    ...         "   .. gp-sphinx-documented-field: demo.Item value",
    ...         "   .. attribute:: value",
    ...         "",
    ...         "      Horizontal offset.",
    ...         "",
    ...         "      :type: int",
    ...     ],
    ...     ".. gp-sphinx-documented-field: demo.Item ",
    ... )
    {'value': ['Horizontal offset.']}
    """
    bodies: dict[str, list[str]] = {}
    lines = list(lines)
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped.startswith(marker_prefix):
            continue
        name = stripped[len(marker_prefix) :].strip()
        marker_indent = len(line) - len(stripped)
        directive_index = index + 1
        if directive_index >= len(lines) or not lines[
            directive_index
        ].lstrip().startswith(_ATTRIBUTE_DIRECTIVE):
            continue

        block: list[str] = []
        for candidate in lines[directive_index + 1 :]:
            candidate_stripped = candidate.lstrip()
            if (
                candidate_stripped
                and len(candidate) - len(candidate_stripped) <= marker_indent
            ):
                break
            block.append(candidate)

        body = _strip_rendered_fields(textwrap.dedent("\n".join(block)).splitlines())
        if body:
            bodies[name] = body
    return bodies


_ACTIVE_FIELD_DOCS: list[dict[str, list[str]]] = []


def active_field_doc(name: str) -> list[str] | None:
    """Return the ``Attributes`` prose for *name* on the class being rendered.

    Consulted by the attribute documenter while a class documents its
    members, so a member autodoc renders concretely — a class variable, a
    slot-free pseudo-field, an undocumented property — can carry the
    description its owner's ``Attributes`` entry wrote.

    Parameters
    ----------
    name : str
        Bare member name under consideration.

    Returns
    -------
    list[str] | None
        Description lines, or ``None`` when nothing described *name*.

    Examples
    --------
    >>> active_field_doc("value") is None
    True
    """
    if not _ACTIVE_FIELD_DOCS:
        return None
    return _ACTIVE_FIELD_DOCS[-1].get(name)


class FieldDocFallbackMixin:
    """Describe a bare member from its owner's ``Attributes`` entry.

    A class variable, an init-only dataclass field, and a property
    without a docstring all reach the page as a signature with nothing
    beneath it: ``NonDataDescriptorMixin.get_doc`` returns ``None`` for a
    plain class-level value, and an undocumented property has no
    docstring to return. A ``#:`` source comment is the one description
    autodoc already reattaches at that point. This does the same for the
    description the owning class wrote, so the entry keeps the prose its
    author supplied alongside the annotation and value only autodoc can
    render.
    """

    objpath: list[str]

    def get_doc(self) -> list[list[str]] | None:
        """Return the member's own docstring, or its owner's description.

        Returns
        -------
        list[list[str]] | None
            Docstring blocks, or ``None`` when nothing describes the member.

        Examples
        --------
        >>> FieldDocFallbackMixin.get_doc  # doctest: +ELLIPSIS
        <function FieldDocFallbackMixin.get_doc at 0x...>
        """
        doc = t.cast(t.Any, super()).get_doc()
        if doc and any(line.strip() for block in doc for line in block):
            return t.cast("list[list[str]] | None", doc)
        if not self.objpath:
            return t.cast("list[list[str]] | None", doc)
        fallback = active_field_doc(self.objpath[-1])
        if fallback is None:
            return t.cast("list[list[str]] | None", doc)
        return [list(fallback)]


class GpPropertyDocumenter(FieldDocFallbackMixin, PropertyDocumenter):  # type: ignore[misc]
    """``PropertyDocumenter`` that honors an owner's ``Attributes`` entry."""

    objtype = "property"
    priority = PropertyDocumenter.priority + 1


class _RenderedFieldsDocumenterMixin:
    """Resolve field ownership after the wrapped documenter renders members."""

    directive: t.Any
    fullname: str
    indent: str
    objpath: list[str]

    def document_members(self, all_members: bool = False) -> None:
        """Render members, then remove only replaced field directives.

        Parameters
        ----------
        all_members : bool
            Whether the wrapped documenter was asked to include every member.

        Examples
        --------
        >>> _RenderedFieldsDocumenterMixin.document_members  # doctest: +ELLIPSIS
        <function _RenderedFieldsDocumenterMixin.document_members at 0x...>
        """
        result = t.cast(StringList, self.directive.result)
        marker_prefix = f"{_FIELD_MARKER}{self.fullname} "
        candidates = {
            line.lstrip()[len(marker_prefix) :].strip()
            for line in result
            if line.lstrip().startswith(marker_prefix)
        }
        member_start = len(result)
        _ACTIVE_FIELD_DOCS.append(_field_doc_bodies(result, marker_prefix))
        try:
            t.cast(t.Any, super()).document_members(all_members)
        finally:
            _ACTIVE_FIELD_DOCS.pop()
        rendered = _rendered_field_names(
            result.data[member_start:],
            self.objpath,
            candidates,
            self.indent,
        )
        _resolve_marked_fields(result, self.fullname, rendered)


def _wrap_documenter(documenter: type[Documenter]) -> type[Documenter]:
    """Wrap a registered class-like documenter without replacing its behavior.

    Parameters
    ----------
    documenter : type[sphinx.ext.autodoc.Documenter]
        Final documenter registered by the loaded extension stack.

    Returns
    -------
    type[sphinx.ext.autodoc.Documenter]
        A subclass resolving marked fields after member rendering.

    Examples
    --------
    >>> _wrap_documenter  # doctest: +ELLIPSIS
    <function _wrap_documenter at 0x...>
    """
    if issubclass(documenter, _RenderedFieldsDocumenterMixin):
        return documenter
    wrapped = type(
        f"RenderedFields{documenter.__name__}",
        (_RenderedFieldsDocumenterMixin, documenter),
        {"__module__": documenter.__module__},
    )
    return t.cast("type[Documenter]", wrapped)


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
    carries declared fields into ``autodoc-skip-member``; transient markers
    carry other field directives into post-render ownership resolution.

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
    lines[:] = _coalesce_attribute_directives(lines, documented)
    if options.no_index or options.noindex:
        _add_attribute_no_index(lines)
    names = _attribute_directive_names(lines) | documented
    _mark_attribute_directives(lines, name)
    _PROCESSED_FIELDS[app] = _ProcessedFields(
        options=options,
        owner=obj,
        names=names,
    )


def _prepare_documented_fields(app: Sphinx) -> None:
    """Install field finalization after every extension has initialized.

    Wrap the final class and exception documenters already registered by the
    extension stack, then install the final docstring processor.

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
    for objtype in _CLASS_LIKE_AUTODOC_TYPES:
        documenter = app.registry.documenters.get(objtype)
        if documenter is not None:
            app.add_autodocumenter(
                _wrap_documenter(documenter),
                override=True,
            )
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
    app.add_autodocumenter(GpPropertyDocumenter, override=True)
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
