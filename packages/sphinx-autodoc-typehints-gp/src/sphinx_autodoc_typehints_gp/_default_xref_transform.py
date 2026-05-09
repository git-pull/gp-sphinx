"""Cross-reference identifiers inside parameter default values.

After Stage A (Sphinx's ``autodoc_preserve_defaults`` plus the
synthetic-init listener in :mod:`._param_defaults`) the arglist is
parseable and Sphinx emits ``nodes.inline(classes=['default_value'])``
spans containing the source text of each default. Sphinx never
creates :class:`~sphinx.addnodes.pending_xref` nodes for default
values — only for type annotations.

This module ships :class:`DefaultValueXrefTransform`, a
:class:`~sphinx.transforms.post_transforms.SphinxPostTransform` that
walks every ``default_value`` span inside an
:class:`~sphinx.addnodes.desc_parameter`, ``ast.parse``s its text,
and replaces the span's plain-text children with a mix of
``nodes.Text`` and ``pending_xref`` nodes — using the same
``:py:class:``-styled ``nodes.literal`` wrapping that Sphinx's
``XRefRole`` produces in inline prose:

.. code-block:: html

   <a class="reference internal" href="#mod.Foo" title="mod.Foo">
     <code class="xref py py-class docutils literal notranslate">
       <span class="pre">Foo</span>
     </code>
   </a>

Priority is **5** — strictly below
:class:`~sphinx.transforms.post_transforms.ReferencesResolver`'s
priority of 10 — so the ``pending_xref`` nodes we create are still
unresolved when the resolver runs.

For unsupported AST shapes (lambdas, comprehensions, generator
expressions) the transform leaves the span untouched, which keeps
the existing plain-text rendering.
"""

from __future__ import annotations

import ast
import logging
import typing as t

from docutils import nodes
from sphinx import addnodes
from sphinx.transforms.post_transforms import SphinxPostTransform

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)


def _xref(
    target: str,
    title: str,
    *,
    py_module: str | None = None,
    py_class: str | None = None,
) -> addnodes.pending_xref:
    """Build a ``:py:class:``-styled pending_xref for *target*.

    The contnode is ``nodes.literal('', '', nodes.Text(title),
    classes=['xref', 'py', 'py-class'])`` — exactly the shape an
    inline ``:py:class:`target``` role would produce, so the
    rendered HTML matches that of normal class references.

    *py_module* and *py_class* mirror the ``ref_context`` keys
    Sphinx's Python domain reads when resolving references. Passing
    them lets unqualified targets like ``Foo`` resolve against the
    surrounding ``desc_signature``'s module.

    Examples
    --------
    >>> n = _xref('mod.Foo', 'Foo')
    >>> n['reftarget']
    'mod.Foo'
    >>> n['reftype']
    'class'
    >>> isinstance(n.children[0], nodes.literal)
    True
    """
    literal = nodes.literal(
        "",
        "",
        nodes.Text(title),
        classes=["xref", "py", "py-class"],
    )
    xref = addnodes.pending_xref(
        "",
        literal,
        refdomain="py",
        reftype="class",
        reftarget=target,
        refexplicit=False,
        refwarn=False,
    )
    if py_module is not None:
        xref["py:module"] = py_module
    if py_class is not None:
        xref["py:class"] = py_class
    return xref


def _ast_to_nodes(
    node: ast.AST,
    *,
    py_module: str | None = None,
    py_class: str | None = None,
) -> list[nodes.Node]:
    """Convert an ``ast`` expression node into docutils inline nodes.

    Identifier-emitting branches (``ast.Name``, ``ast.Attribute``)
    produce ``pending_xref`` nodes whose contnode is a
    ``:py:class:``-styled ``nodes.literal``. Constants emit
    ``nodes.Text`` matching ``repr(value)``. Containers
    (Tuple/List/Set) and Call expressions emit punctuation as
    ``nodes.Text``.

    *py_module* / *py_class* are forwarded to every ``pending_xref``
    so that unqualified targets resolve against the surrounding
    ``desc_signature``'s module/class context.

    Raises ``SyntaxError`` for unsupported shapes (lambdas,
    comprehensions, generator expressions, dict/set literals,
    operators we haven't taught it about). Callers catch and fall
    back to the original text.

    Examples
    --------
    >>> _ast_to_nodes(ast.parse('Foo', mode='eval').body)[0]['reftarget']
    'Foo'
    >>> _ast_to_nodes(ast.parse('mod.Foo', mode='eval').body)[0]['reftarget']
    'mod.Foo'
    >>> [n.astext() for n in _ast_to_nodes(ast.parse('42', mode='eval').body)]
    ['42']
    """
    if isinstance(node, ast.Name):
        return [_xref(node.id, node.id, py_module=py_module, py_class=py_class)]
    if isinstance(node, ast.Attribute):
        path = _attr_chain(node)
        if path is None:
            msg = f"unsupported attribute base: {ast.dump(node)}"
            raise SyntaxError(msg)
        return [_xref(path, path, py_module=py_module, py_class=py_class)]
    if isinstance(node, ast.Constant):
        if node.value is Ellipsis:
            return [nodes.Text("...")]
        return [nodes.Text(repr(node.value))]
    if isinstance(node, ast.Tuple):
        return _wrap_seq(
            "(",
            ")",
            node.elts,
            force_trailing_comma=len(node.elts) == 1,
            py_module=py_module,
            py_class=py_class,
        )
    if isinstance(node, ast.List):
        return _wrap_seq("[", "]", node.elts, py_module=py_module, py_class=py_class)
    if isinstance(node, ast.Set):
        if not node.elts:
            msg = "empty set literal cannot be parsed"  # ast won't yield this
            raise SyntaxError(msg)
        return _wrap_seq("{", "}", node.elts, py_module=py_module, py_class=py_class)
    if isinstance(node, ast.Call):
        result: list[nodes.Node] = []
        result.extend(_ast_to_nodes(node.func, py_module=py_module, py_class=py_class))
        result.append(nodes.Text("("))
        first = True
        for arg in node.args:
            if not first:
                result.append(nodes.Text(", "))
            result.extend(_ast_to_nodes(arg, py_module=py_module, py_class=py_class))
            first = False
        for kw in node.keywords:
            if not first:
                result.append(nodes.Text(", "))
            result.append(nodes.Text(f"{kw.arg}="))
            result.extend(
                _ast_to_nodes(kw.value, py_module=py_module, py_class=py_class)
            )
            first = False
        result.append(nodes.Text(")"))
        return result
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return [
            nodes.Text("-"),
            *_ast_to_nodes(node.operand, py_module=py_module, py_class=py_class),
        ]
    msg = f"unsupported expression: {ast.dump(node)}"
    raise SyntaxError(msg)


def _wrap_seq(
    opener: str,
    closer: str,
    elts: list[ast.expr],
    *,
    force_trailing_comma: bool = False,
    py_module: str | None = None,
    py_class: str | None = None,
) -> list[nodes.Node]:
    """Render ``[a, b, c]`` / ``(a, b, c)`` style sequences.

    *force_trailing_comma* renders a trailing comma after the only
    element of a 1-tuple to disambiguate ``(x,)`` from ``(x)``.
    """
    result: list[nodes.Node] = [nodes.Text(opener)]
    first = True
    for elt in elts:
        if not first:
            result.append(nodes.Text(", "))
        result.extend(_ast_to_nodes(elt, py_module=py_module, py_class=py_class))
        first = False
    if force_trailing_comma:
        result.append(nodes.Text(","))
    result.append(nodes.Text(closer))
    return result


def _attr_chain(node: ast.Attribute) -> str | None:
    """Reduce ``a.b.c`` Attribute chains to a dotted string.

    Returns ``None`` if the leftmost base isn't a Name (e.g. a
    function-call result like ``foo().bar`` — too dynamic to
    cross-reference statically).
    """
    parts: list[str] = [node.attr]
    current: ast.expr = node.value
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return ".".join(reversed(parts))


def _transform_default_value_span(
    span: nodes.inline,
    *,
    py_module: str | None = None,
    py_class: str | None = None,
) -> bool:
    """Mutate *span*'s children with cross-referenced AST nodes.

    *py_module* / *py_class* are forwarded to each ``pending_xref``
    so unqualified identifiers resolve against the surrounding
    ``desc_signature``'s module/class.

    Returns ``True`` if children were rewritten, ``False`` if the
    span was left untouched (unsupported AST shape, parse failure,
    or empty content).

    Examples
    --------
    >>> from docutils import nodes
    >>> span = nodes.inline("", "Foo", classes=["default_value"])
    >>> _transform_default_value_span(span)
    True
    >>> span = nodes.inline("", "lambda: 1", classes=["default_value"])
    >>> _transform_default_value_span(span)  # unparseable -> untouched
    False
    >>> span = nodes.inline("", "   ", classes=["default_value"])
    >>> _transform_default_value_span(span)  # whitespace-only
    False
    """
    text = span.astext()
    if not text.strip():
        return False
    try:
        tree = ast.parse(text, mode="eval")
        new_children = _ast_to_nodes(tree.body, py_module=py_module, py_class=py_class)
    except SyntaxError:
        return False
    if not new_children:
        return False
    span.clear()
    span.extend(new_children)
    return True


def _enclosing_signode_context(
    parameter: addnodes.desc_parameter,
) -> tuple[str | None, str | None]:
    """Read ``module``/``class`` attributes off the enclosing ``desc_signature``.

    Returns ``(None, None)`` when *parameter* has no ``desc_signature``
    ancestor — typically because the test harness builds a bare
    ``desc_parameter`` outside a real Sphinx tree.

    Examples
    --------
    >>> from sphinx import addnodes
    >>> sig = addnodes.desc_signature("", "", module="libtmux.session",
    ...                                class_=None)
    >>> sig["class"] = "Session"
    >>> param = addnodes.desc_parameter()
    >>> sig.append(param)
    >>> _enclosing_signode_context(param)
    ('libtmux.session', 'Session')
    >>> _enclosing_signode_context(addnodes.desc_parameter())
    (None, None)
    """
    parent = parameter.parent
    while parent is not None and not isinstance(parent, addnodes.desc_signature):
        parent = parent.parent
    if parent is None:
        return None, None
    return parent.get("module"), parent.get("class")


class DefaultValueXrefTransform(SphinxPostTransform):
    """Convert identifier text inside ``default_value`` spans to live xrefs.

    Walks every ``nodes.inline`` whose ``classes`` includes
    ``'default_value'`` *inside* a
    :class:`~sphinx.addnodes.desc_parameter`, AST-parses the text,
    and replaces it with mixed-node output that includes
    :class:`~sphinx.addnodes.pending_xref` for each identifier.

    Hand-written ``.. py:function:: foo(x=Bar)`` directives are
    handled identically because they emit the same span structure.
    """

    default_priority = 5

    def run(self, **kwargs: t.Any) -> None:
        """Walk every desc_parameter's default_value span and rewrite it."""
        del kwargs
        config_flag = getattr(
            self.app.config,
            "gp_typehints_curate_param_defaults",
            True,
        )
        if not config_flag:
            return
        for parameter in self.document.findall(addnodes.desc_parameter):
            py_module, py_class = _enclosing_signode_context(parameter)
            for span in parameter.findall(nodes.inline):
                classes = span.get("classes") or []
                if "default_value" not in classes:
                    continue
                _transform_default_value_span(
                    span,
                    py_module=py_module,
                    py_class=py_class,
                )


def register(app: Sphinx) -> None:
    """Register the transform with the Sphinx app.

    Examples
    --------
    >>> register  # doctest: +ELLIPSIS
    <function register at 0x...>
    """
    app.add_post_transform(DefaultValueXrefTransform)
