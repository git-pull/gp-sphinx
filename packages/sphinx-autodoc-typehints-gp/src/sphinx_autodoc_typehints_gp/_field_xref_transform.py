"""Canonicalise Python xref styling inside autodoc field lists.

Sphinx's ``util/docfields.py`` and gp-sphinx's own
:func:`~sphinx_autodoc_typehints_gp.extension._annotation_to_nodes`
produce three different contnode shapes inside the
:class:`~sphinx.addnodes.pending_xref` nodes used by autodoc field
lists (Parameters, Returns, Return type, Raises, Yields):

- ``TypedField.make_field`` wraps **param types** in
  :class:`sphinx.addnodes.literal_emphasis` (``<em>``).
- ``GroupedField.make_field`` wraps **raises exception names** in
  :class:`sphinx.addnodes.literal_strong` (``<strong>``).
- typehints-gp's ``_annotation_to_nodes`` emits ``pending_xref``
  whose contnode is a bare :class:`docutils.nodes.Text`.

None of these match the inline ``:py:class:`` / ``:py:obj:`` HTML
shape produced by :class:`~sphinx.roles.XRefRole`:

.. code-block:: html

   <a class="reference internal" href="…">
     <code class="xref py py-class docutils literal notranslate">
       <span class="pre">Server</span>
     </code>
   </a>

This module ships :class:`FieldListXrefStyleTransform`, a
:class:`~sphinx.transforms.post_transforms.SphinxPostTransform`
running at priority **5** (below
:class:`~sphinx.transforms.post_transforms.ReferencesResolver`'s 10,
identical to :mod:`._default_xref_transform`'s priority slot) that
walks every Python-domain ``pending_xref`` inside a
:class:`docutils.nodes.field_list` ancestor and rewrites the
contnode children to a single
``nodes.literal('', '', nodes.Text(title), classes=['xref', 'py',
'<role-class>'])`` — the canonical XRefRole shape.

The role class is chosen from the enclosing field's name:

- ``type X`` / ``rtype`` / ``ytype`` / ``yieldtype`` → ``py-class``.
- ``raises`` / ``raise`` / ``except`` → ``py-exc``.
- Anything else → ``py-obj`` (matches the default-value transform's
  generic fallback).

It also sets ``refspecific=True`` so the Python domain's
``searchmode=1`` cross-module fuzzy lookup runs (otherwise
``Server`` documented under ``libtmux.server`` wouldn't resolve from
a method documented under ``libtmux.session``; same fix logic as
:mod:`._default_xref_transform`).

A second transform :class:`FieldListPrefixWrapTransform` (priority
**6**, runs after the xref normalisation) wraps the prefix portion
of each field-list ``<dd>`` paragraph (everything before the
em-dash separator) in a
``nodes.inline(classes=['gp-sphinx-field-prefix'])`` so the CSS in
``_static/css/typehints_gp.css`` can render the prefix in monospace
without disturbing the description text after the em-dash.
"""

from __future__ import annotations

import typing as t

from docutils import nodes
from sphinx import addnodes
from sphinx.transforms.post_transforms import SphinxPostTransform

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx


_EXC_FIELD_TOKENS: t.Final = ("raise", "except")


def _role_class_for_field_name(field_name: str) -> str:
    """Map a field-list field name to the canonical xref role class.

    Defaults to ``py-class`` because field-list xrefs almost always
    reference Python identifier types (parameter types, return types,
    yield types, prose references inside descriptions). Carves out
    ``py-exc`` for ``:raises:`` / ``:except:`` field labels — including
    Napoleon's merged ``Raises`` heading — so the rendered ``<code>``
    role advertises the correct semantic.

    Examples
    --------
    >>> _role_class_for_field_name('type server')
    'py-class'
    >>> _role_class_for_field_name('rtype')
    'py-class'
    >>> _role_class_for_field_name('Parameters')
    'py-class'
    >>> _role_class_for_field_name('Returns')
    'py-class'
    >>> _role_class_for_field_name('raises')
    'py-exc'
    >>> _role_class_for_field_name('Raises')
    'py-exc'
    >>> _role_class_for_field_name('except OSError')
    'py-exc'
    >>> _role_class_for_field_name('')
    'py-class'
    """
    name = field_name.strip().lower()
    if any(token in name for token in _EXC_FIELD_TOKENS):
        return "py-exc"
    return "py-class"


def _enclosing_field_name(node: nodes.Element) -> str:
    """Return the text of the ``field_name`` for *node*'s enclosing field.

    Walks up the ancestor chain until a :class:`nodes.field` is found,
    then reads its first child (the ``field_name`` element). Returns
    an empty string if no enclosing field is present.

    Examples
    --------
    >>> from docutils import nodes
    >>> from sphinx import addnodes
    >>> field = nodes.field()
    >>> field += nodes.field_name('', 'type server')
    >>> body = nodes.field_body()
    >>> xref = addnodes.pending_xref('', refdomain='py')
    >>> body += xref
    >>> field += body
    >>> _enclosing_field_name(xref)
    'type server'
    >>> _enclosing_field_name(addnodes.pending_xref())
    ''
    """
    parent: t.Any = node.parent
    while parent is not None and not isinstance(parent, nodes.field):
        parent = parent.parent
    if parent is None:
        return ""
    if not parent.children:
        return ""
    name_node = parent.children[0]
    if isinstance(name_node, nodes.field_name):
        return name_node.astext()
    return ""


def _normalize_xref_contnode(xref: addnodes.pending_xref) -> bool:
    """Replace *xref*'s children with a role-class-aware ``<code>`` literal.

    The role class is chosen by :func:`_role_class_for_field_name`
    from the enclosing field's name — ``py-class`` for type/return-
    type/yield-type fields, ``py-exc`` for ``:raises:`` fields. The
    rewritten literal carries ``classes=['xref', 'py', '<role>']`` so
    Sphinx's ``XRefRole`` HTML shape is reproduced.

    Returns ``True`` if children were rewritten, ``False`` if the
    xref was left untouched (non-Python domain or empty title).

    Examples
    --------
    >>> from docutils import nodes
    >>> from sphinx import addnodes
    >>> field = nodes.field()
    >>> field += nodes.field_name('', 'type server')
    >>> body = nodes.field_body()
    >>> xref = addnodes.pending_xref(
    ...     '', nodes.Text('Server'), refdomain='py', reftarget='Server'
    ... )
    >>> body += xref
    >>> field += body
    >>> _normalize_xref_contnode(xref)
    True
    >>> xref.children[0]['classes']
    ['xref', 'py', 'py-class']
    >>> xref['refspecific']
    True
    >>> exc_field = nodes.field()
    >>> exc_field += nodes.field_name('', 'raises OSError')
    >>> exc_body = nodes.field_body()
    >>> exc_xref = addnodes.pending_xref(
    ...     '', nodes.Text('OSError'), refdomain='py', reftarget='OSError'
    ... )
    >>> exc_body += exc_xref
    >>> exc_field += exc_body
    >>> _normalize_xref_contnode(exc_xref)
    True
    >>> exc_xref.children[0]['classes']
    ['xref', 'py', 'py-exc']
    >>> _normalize_xref_contnode(addnodes.pending_xref('', refdomain='c'))
    False
    """
    if xref.get("refdomain") != "py":
        return False
    title = xref.astext()
    if not title:
        return False
    role_class = _role_class_for_field_name(_enclosing_field_name(xref))
    literal = nodes.literal(
        "",
        "",
        nodes.Text(title),
        classes=["xref", "py", role_class],
    )
    xref.clear()
    xref.append(literal)
    # `refspecific` triggers `searchmode=1` in `PythonDomain.find_obj`
    # so unqualified targets match across documented modules. Same
    # rationale as the default-value xref transform; without it,
    # cross-module identifiers like libtmux's `Server` referenced
    # from a `libtmux.session.Session.method` field would silently
    # fail to resolve.
    xref["refspecific"] = True
    return True


class FieldListXrefStyleTransform(SphinxPostTransform):
    """Normalise contnodes of Python xrefs inside autodoc field lists.

    Runs before :class:`~sphinx.transforms.post_transforms.ReferencesResolver`
    (priority 10) so the rewritten contnodes pass through reference
    resolution intact. Scoped to ``pending_xref`` nodes inside a
    :class:`docutils.nodes.field_list` ancestor — does not touch xrefs
    in body prose, signatures, or other contexts (those have their
    own canonicalised shapes already).
    """

    default_priority = 5

    def run(self, **kwargs: t.Any) -> None:
        """Rewrite every Python-domain xref inside any field_list."""
        del kwargs
        for field_list in self.document.findall(nodes.field_list):
            for xref in field_list.findall(addnodes.pending_xref):
                _normalize_xref_contnode(xref)


_EN_DASH = "\N{EN DASH}"


def _is_em_dash_separator(text: str) -> bool:
    """Detect Sphinx's prefix/description em-dash separator.

    Sphinx renders the boundary between a field-list prefix and its
    description as a Text node containing the en-dash character
    (U+2013) surrounded by spaces, or the ASCII fallback ``" -- "``.
    This predicate matches both shapes so the wrapper transform can
    locate the split.

    Examples
    --------
    >>> _is_em_dash_separator(f' {chr(0x2013)} ')
    True
    >>> _is_em_dash_separator(' -- description')
    True
    >>> _is_em_dash_separator('item: ')
    False
    """
    stripped = text.lstrip()
    return stripped.startswith(_EN_DASH + " ") or stripped.startswith("-- ")


_PROSE_FIELD_TOKENS: t.Final = (
    "return",
    "yield",
    "note",
    "example",
    "warning",
    "see also",
    "see-also",
    "tip",
    "summary",
    "description",
)


def _is_prose_field(field_name: str) -> bool:
    """Return True if *field_name* labels a prose-style description field.

    These fields hold free-form description text rather than typed
    parameter rows or identifier-only bodies, so wrapping their
    paragraphs in the monospace prefix would re-style ordinary body
    copy. Detected as ``Returns`` / ``Yields`` / ``Notes`` /
    ``Examples`` / ``Warning`` / ``See Also`` / ``Tip`` / ``Summary``
    / ``Description``. ``Return type`` (which DOES want wrapping) is
    explicitly distinguished by the trailing ``type`` token —
    callers see ``rtype`` / ``return type`` for that variant.

    Examples
    --------
    >>> _is_prose_field('Returns')
    True
    >>> _is_prose_field('returns')
    True
    >>> _is_prose_field('Yields')
    True
    >>> _is_prose_field('Notes')
    True
    >>> _is_prose_field('Return type')
    False
    >>> _is_prose_field('rtype')
    False
    >>> _is_prose_field('ytype')
    False
    >>> _is_prose_field('Parameters')
    False
    >>> _is_prose_field('Raises')
    False
    """
    name = field_name.strip().lower()
    if not name:
        return False
    if "type" in name:
        return False  # 'rtype' / 'return type' / 'ytype' / 'yieldtype'
    return any(token in name for token in _PROSE_FIELD_TOKENS)


def _wrap_prefix_in_paragraph(
    paragraph: nodes.paragraph,
    *,
    field_name: str = "",
) -> bool:
    """Wrap the prefix children of *paragraph* in a monospace inline.

    The prefix is the run of children before the first em-dash text
    separator. If no separator exists (e.g. ``:rtype:`` /
    ``:raises:`` rows whose entire content is a single identifier),
    wraps the full child list.

    Skipped for prose-style fields (``Returns`` / ``Yields`` /
    ``Notes`` / ``Examples`` etc.) where the body is free-form
    description text — wrapping those paragraphs would re-style
    ordinary body copy and clash with embedded inline ``<code>``
    spans like ``:any:`None```.

    Returns ``True`` if a wrapper was added, ``False`` if the
    paragraph was already wrapped, lives inside a prose field, or
    otherwise had no eligible content.
    """
    if not paragraph.children:
        return False
    if _is_prose_field(field_name):
        return False
    # Skip paragraphs that already have our wrapper as the first child.
    first = paragraph.children[0]
    if isinstance(first, nodes.inline) and "gp-sphinx-field-prefix" in (
        first.get("classes") or []
    ):
        return False
    split_index = len(paragraph.children)
    for index, child in enumerate(paragraph.children):
        if isinstance(child, nodes.Text) and _is_em_dash_separator(str(child)):
            split_index = index
            break
    prefix_children = list(paragraph.children[:split_index])
    rest_children = list(paragraph.children[split_index:])
    if not prefix_children:
        return False
    wrapper = nodes.inline("", "", classes=["gp-sphinx-field-prefix"])
    wrapper.extend(prefix_children)
    paragraph.clear()
    paragraph.append(wrapper)
    paragraph.extend(rest_children)
    return True


class FieldListPrefixWrapTransform(SphinxPostTransform):
    """Wrap the field-list prefix portion in a monospace inline.

    For each ``<dd>`` (``nodes.field_body``) of every
    ``nodes.field_list``, wraps the leading children of the first
    paragraph (everything before the em-dash separator) in
    ``nodes.inline(classes=['gp-sphinx-field-prefix'])`` so a single
    CSS rule can render the prefix in monospace without affecting
    the description text.

    Bullet-list field bodies (e.g. ``:raises:`` lists) are walked
    one item at a time so each ``<li>``'s paragraph gets its own
    wrapper. Field bodies with no em-dash (no description portion)
    get the entire paragraph wrapped.

    Runs after :class:`FieldListXrefStyleTransform` so the wrapper
    contains the canonicalised xref nodes.
    """

    default_priority = 6

    def run(self, **kwargs: t.Any) -> None:
        """Walk every field_body's paragraphs and wrap their prefixes."""
        del kwargs
        for field_list in self.document.findall(nodes.field_list):
            for field in field_list.findall(nodes.field):
                if not field.children:
                    continue
                name_node = field.children[0]
                field_name = (
                    name_node.astext()
                    if isinstance(name_node, nodes.field_name)
                    else ""
                )
                for body in field.findall(nodes.field_body):
                    for paragraph in body.findall(nodes.paragraph):
                        _wrap_prefix_in_paragraph(paragraph, field_name=field_name)


def register(app: Sphinx) -> None:
    """Register both field-list transforms with the Sphinx app.

    Examples
    --------
    >>> register  # doctest: +ELLIPSIS
    <function register at 0x...>
    """
    app.add_post_transform(FieldListXrefStyleTransform)
    app.add_post_transform(FieldListPrefixWrapTransform)
