"""Drop autodoc field stubs a NumPy ``Attributes`` section already describes.

:class:`typing.NamedTuple` compiles every field into a ``_tuplegetter``
descriptor whose ``__doc__`` is the boilerplate ``"Alias for field number N"``.
Autodoc counts that boilerplate as a real docstring, so the field is emitted as
its own ``py:attribute`` regardless of how ``undoc-members`` is set.

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
import sys
import typing as t

from sphinx_autodoc_typehints_gp._numpy_docstring import process_numpy_docstring

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.ext.autodoc._legacy_class_based._directive_options import (  # type: ignore[import-not-found]
        Options,
    )

_ATTRIBUTE_DIRECTIVE = ".. attribute:: "


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
    - that class exposes a ``_fields`` tuple containing *name*
      (:class:`typing.NamedTuple` and anything shaped like it);
    - *obj* is the attribute the class itself exposes under *name*;
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

    fields = getattr(owner, "_fields", None)
    if not isinstance(fields, tuple) or name not in fields:
        return None
    if inspect.getattr_static(owner, name, None) is not obj:
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
