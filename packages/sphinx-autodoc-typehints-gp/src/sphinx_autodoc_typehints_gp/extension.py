"""Type annotation enhancement and NumPy docstring parsing for Sphinx autodoc.

Replaces both ``sphinx-autodoc-typehints`` and ``sphinx.ext.napoleon`` with a
single self-contained extension.  Two independent pipelines run in sequence:

1. **NumPy docstring parsing** — ``process_docstring`` hooks
   ``autodoc-process-docstring`` to convert NumPy section-based docstrings
   (Parameters, Returns, Raises, Yields, …) into RST field lists.  Implemented
   in :mod:`sphinx_autodoc_typehints_gp._numpy_docstring`.

2. **Type cross-referencing** — ``merge_typehints`` hooks
   ``object-description-transform`` at priority 499 (before Sphinx's built-in
   ``_merge_typehints`` at 500) to insert or upgrade ``:type:`` and ``:rtype:``
   field nodes with cross-referenced ``pending_xref`` content.

Does **not** use ``exec()``, ``typing.get_type_hints()``, or any
monkeypatches.  Type annotations are resolved statically via AST analysis.
"""

from __future__ import annotations

import ast
import builtins
import inspect
import logging
import sys
import typing as t

from docutils import nodes
from sphinx import addnodes
from sphinx.errors import ExtensionError

if t.TYPE_CHECKING:
    from docutils.nodes import Element, Node
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.ext.autodoc._legacy_class_based._directive_options import (  # type: ignore[import-not-found]
        Options,
    )

logger = logging.getLogger(__name__)

_MODULE_IMPORTS: dict[str, dict[str, str]] = {}


def get_module_imports(module_name: str) -> dict[str, str]:
    """Extract all import aliases from a module's source code.

    Parses the AST of the module to find all ``import`` and
    ``from ... import`` statements, including those inside
    ``if TYPE_CHECKING:`` blocks.

    Parameters
    ----------
    module_name : str
        The fully qualified name of the module to inspect.

    Returns
    -------
    dict[str, str]
        A mapping of local names to fully qualified names.

    Examples
    --------
    >>> import sphinx.util.typing
    >>> aliases = get_module_imports('sphinx.util.typing')
    >>> aliases['Any']
    'typing.Any'
    """
    if module_name in _MODULE_IMPORTS:
        return _MODULE_IMPORTS[module_name]

    module = sys.modules.get(module_name)
    if not module:
        return {}
    try:
        source = inspect.getsource(module)
    except (TypeError, OSError):
        return {}

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                aliases[name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level > 0:
                parts = module_name.split(".")
                if len(parts) >= node.level:
                    base = ".".join(parts[: -node.level])
                    if base:
                        mod = f"{base}.{mod}" if mod else base
            for alias in node.names:
                name = alias.asname or alias.name
                aliases[name] = f"{mod}.{alias.name}" if mod else alias.name

    _MODULE_IMPORTS[module_name] = aliases
    return aliases


class _TypeTransformer(ast.NodeTransformer):
    """AST transformer that rewrites type annotation names to Sphinx xrefs.

    Each bare name in a type annotation string is replaced with its
    fully-qualified alias using Sphinx's ``~`` cross-reference prefix.
    For example, a bare ``List`` becomes ``~typing.List``; a local
    ``MyClass`` (imported as ``from other import MyClass``) becomes
    ``~other.MyClass``.  Attribute chains are collapsed: if the alias
    for ``alias`` is ``~typing``, then ``alias.List`` collapses to
    ``~typing.List``.

    The import alias map is built by :func:`get_module_imports` from the
    module's AST, including names guarded by ``if TYPE_CHECKING:`` blocks
    — so forward references that are only importable at type-check time
    are resolved correctly without any runtime evaluation.
    """

    def __init__(
        self,
        module_name: str,
        aliases: dict[str, str],
        *,
        qualify_unresolved: bool,
    ) -> None:
        self.module_name = module_name
        self.aliases = aliases
        self.qualify_unresolved = qualify_unresolved

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id in self.aliases:
            return ast.Name(id=f"~{self.aliases[node.id]}", ctx=node.ctx)
        if hasattr(builtins, node.id):
            return node
        if not self.qualify_unresolved:
            return node
        return ast.Name(id=f"~{self.module_name}.{node.id}", ctx=node.ctx)

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id.startswith("~"):
            return ast.Name(id=f"{node.value.id}.{node.attr}", ctx=node.ctx)
        return node


def resolve_annotation_string(
    ann_str: str,
    module_name: str,
    aliases: dict[str, str],
    *,
    qualify_unresolved: bool = True,
) -> str:
    """Resolve a string annotation to use fully qualified names.

    Parameters
    ----------
    ann_str : str
        The string representation of the type annotation.
    module_name : str
        The name of the module where the annotation is defined.
    aliases : dict[str, str]
        A mapping of local names to fully qualified names.

    Returns
    -------
    str
        The resolved annotation string with ``~`` prefixes for Sphinx.

    Examples
    --------
    >>> aliases = {'List': 'typing.List', 'MyClass': 'other.MyClass'}
    >>> resolve_annotation_string('List[MyClass]', 'my_module', aliases)
    '~typing.List[~other.MyClass]'
    >>> resolve_annotation_string(
    ...     'PathLike[str]',
    ...     'my_module',
    ...     {'PathLike': 'os.PathLike'},
    ...     qualify_unresolved=False,
    ... )
    '~os.PathLike[str]'
    """
    try:
        tree = ast.parse(ann_str, mode="eval")
    except SyntaxError:
        return ann_str

    transformed = _TypeTransformer(
        module_name,
        aliases,
        qualify_unresolved=qualify_unresolved,
    ).visit(tree)
    return ast.unparse(transformed)


def _annotation_to_nodes(annotation: str, env: BuildEnvironment) -> list[Node]:
    """Convert a stringified annotation to cross-referenced docutils nodes.

    Delegates to ``sphinx.domains.python._annotations._parse_annotation``
    which produces ``pending_xref`` nodes for type names and
    ``desc_sig_*`` nodes for punctuation.  Falls back to the re-exported
    name at the Python-domain package level for Sphinx < 7.2.

    ``_parse_annotation`` catches internal ``SyntaxError`` and returns a
    single ``type_to_xref`` node when parsing fails — no extra error
    handling is needed here.

    Parameters
    ----------
    annotation : str
        Stringified type annotation, e.g. ``'str | None'`` or
        ``'dict[str, list[int]]'``.
    env : BuildEnvironment
        Sphinx build environment used for module/class context.

    Returns
    -------
    list[Node]
        Docutils nodes with ``pending_xref`` entries for resolvable names.

    Examples
    --------
    >>> _annotation_to_nodes  # doctest: +ELLIPSIS
    <function _annotation_to_nodes at 0x...>
    """
    try:
        from sphinx.domains.python._annotations import (
            _parse_annotation,
        )
    except ImportError:  # Sphinx < 7.2
        from sphinx.domains.python import (  # type: ignore[attr-defined]
            _parse_annotation,
        )
    return _parse_annotation(annotation, env)


def _enhance_existing_type_field(
    field: nodes.field,
    env: BuildEnvironment,
) -> None:
    """Upgrade a plain-text ``:type:`` or ``:rtype:`` field body to xrefs.

    Called on fields that already exist in the field list — typically
    produced by ``sphinx.ext.napoleon`` from NumPy / Google docstring type
    annotations.  Replaces a single-paragraph plain-text body with
    ``pending_xref`` nodes so types become clickable links.

    The upgrade is skipped when:

    - the field body is not exactly one paragraph (multi-node bodies are
      assumed to be intentionally complex)
    - the paragraph already contains a ``pending_xref`` node (already
      cross-referenced)
    - the paragraph text is empty

    Parameters
    ----------
    field : nodes.field
        A ``:type X:`` or ``:rtype:`` field whose body may contain
        plain text to be enhanced.
    env : BuildEnvironment
        Sphinx build environment.
    """
    if len(field.children) < 2:
        return
    body = field.children[1]
    if not isinstance(body, nodes.field_body):
        return
    if len(body.children) != 1 or not isinstance(body.children[0], nodes.paragraph):
        return
    para = body.children[0]
    if any(isinstance(c, addnodes.pending_xref) for c in para.children):
        return  # already cross-referenced
    text = para.astext().strip()
    if not text:
        return
    para.clear()
    para.extend(_annotation_to_nodes(text, env))


def _strip_hidden_doctest_examples(lines: list[str]) -> None:
    """Drop doctest examples flagged ``# doctest: +HIDE`` from rendered output.

    The example still runs as a test — the doctest runner reads ``__doc__`` from
    source, which this never touches. This only removes it from the
    Sphinx-rendered docstring, so incidental setup (building an ``env`` mapping,
    a socket path) can execute without cluttering the docs. Each ``>>>`` line
    carrying the flag is dropped together with its ``...`` continuation lines.

    Parameters
    ----------
    lines : list[str]
        The docstring lines, modified in place.

    Examples
    --------
    >>> body = [">>> x = 1  # doctest: +HIDE", ">>> x", "1"]
    >>> _strip_hidden_doctest_examples(body)
    >>> body
    ['>>> x', '1']
    """
    kept: list[str] = []
    dropping = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(">>>") and "doctest:" in line and "+HIDE" in line:
            dropping = True
            continue
        if dropping and stripped.startswith("..."):
            continue
        dropping = False
        kept.append(line)
    lines[:] = kept


def process_docstring(
    app: Sphinx,
    what: str,
    name: str,
    obj: t.Any,
    options: Options,
    lines: list[str],
) -> None:
    """Convert NumPy-style docstring sections to RST field lists.

    Hooks ``autodoc-process-docstring`` to replace ``sphinx.ext.napoleon``
    for NumPy-style docstrings.  Delegates to
    :func:`sphinx_autodoc_typehints_gp._numpy_docstring.process_numpy_docstring`.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application instance.
    what : str
        The type of the object being documented.
    name : str
        The fully qualified name of the object.
    obj : t.Any
        The object being documented.
    options : Options
        The options given to the autodoc directive.
    lines : list[str]
        The docstring lines, modified in place.

    Examples
    --------
    >>> process_docstring  # doctest: +ELLIPSIS
    <function process_docstring at 0x...>
    """
    _strip_hidden_doctest_examples(lines)

    from sphinx_autodoc_typehints_gp._numpy_docstring import process_numpy_docstring

    lines[:] = process_numpy_docstring(lines)


def record_typehints(
    app: Sphinx,
    objtype: str,
    name: str,
    obj: t.Any,
    options: Options,
    args: str,
    retann: str,
) -> None:
    """Record type hints to the Sphinx environment.

    Hooks ``autodoc-process-signature`` and extracts annotations directly
    from ``__annotations__``, resolving them statically via AST.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application instance.
    objtype : str
        The type of the object being documented.
    name : str
        The fully qualified name of the object.
    obj : t.Any
        The object being documented.
    options : Options
        The options given to the autodoc directive.
    args : str
        The arguments of the object.
    retann : str
        The return annotation of the object.

    Examples
    --------
    >>> record_typehints  # doctest: +ELLIPSIS
    <function record_typehints at 0x...>
    """
    try:
        annotations = getattr(obj, "__annotations__", None)
        if not annotations:
            return

        module_name = getattr(obj, "__module__", None)
        if not module_name:
            return

        aliases = get_module_imports(module_name)

        doc_annotations = app.env.current_document.autodoc_annotations.setdefault(
            name, {}
        )

        from sphinx.util.typing import stringify_annotation

        for arg_name, annotation in annotations.items():
            if isinstance(annotation, str):
                resolved = resolve_annotation_string(annotation, module_name, aliases)
            else:
                resolved = stringify_annotation(annotation, "smart")
            doc_annotations[arg_name] = resolved

    except (TypeError, ValueError, AttributeError):
        logger.debug("failed to record typehints for %s", name, exc_info=True)


def _modify_field_list(
    node: nodes.field_list,
    annotations: dict[str, str],
    obj_type: str,
    env: BuildEnvironment,
) -> None:
    """Modify a docutils field list to include cross-referenced type annotations.

    Inserts missing ``:type name:`` and ``:rtype:`` fields with
    ``pending_xref`` content.  Fields that already exist (e.g. from Napoleon)
    are left untouched here; ``_enhance_existing_type_field`` handles those.

    Parameters
    ----------
    node : nodes.field_list
        The field list node to modify.
    annotations : dict[str, str]
        The resolved type annotations.
    obj_type : str
        The type of the object (used to suppress ``None`` rtype for classes).
    env : BuildEnvironment
        Sphinx build environment for cross-reference resolution.
    """
    arguments: dict[str, dict[str, bool]] = {}
    fields = t.cast("t.Iterable[nodes.field]", node)
    for field in fields:
        field_name = field[0].astext()
        parts = field_name.split()
        if parts[0] == "param":
            if len(parts) == 2:
                arg = arguments.setdefault(parts[1], {})
                arg["param"] = True
            elif len(parts) > 2:
                name = " ".join(parts[2:])
                arg = arguments.setdefault(name, {})
                arg["param"] = True
                arg["type"] = True
        elif parts[0] == "type":
            name = " ".join(parts[1:])
            arg = arguments.setdefault(name, {})
            arg["type"] = True
        elif parts[0] == "rtype":
            arguments["return"] = {"type": True}

    for name, annotation in annotations.items():
        if name == "return":
            continue

        if "*" + name in arguments:
            name = "*" + name
        elif "**" + name in arguments:
            name = "**" + name

        arg = arguments.get(name, {})

        if not arg.get("type"):
            field = nodes.field()
            field += nodes.field_name("", "type " + name)
            field += nodes.field_body(
                "",
                nodes.paragraph("", "", *_annotation_to_nodes(annotation, env)),
            )
            node += field
        if not arg.get("param"):
            field = nodes.field()
            field += nodes.field_name("", "param " + name)
            field += nodes.field_body("", nodes.paragraph("", ""))
            node += field

    if "return" in annotations and "return" not in arguments:
        annotation = annotations["return"]
        if annotation == "None" and obj_type == "class":
            pass
        else:
            field = nodes.field()
            field += nodes.field_name("", "rtype")
            field += nodes.field_body(
                "",
                nodes.paragraph("", "", *_annotation_to_nodes(annotation, env)),
            )
            node += field


def merge_typehints(
    app: Sphinx, domain: str, obj_type: str, contentnode: Element
) -> None:
    """Merge recorded type hints into the doctree field lists.

    Hooks ``object-description-transform`` at priority 499 — before
    Sphinx's built-in ``_merge_typehints`` at 500.  By the time Sphinx's
    handler runs our cross-referenced fields already exist, so it skips
    its plain-text duplicates.

    For each ``:type:`` / ``:rtype:`` field that Napoleon has already
    inserted as plain text, ``_enhance_existing_type_field`` replaces the
    text content with ``pending_xref`` nodes in-place.

    Only runs when ``autodoc_typehints`` is ``"description"`` or ``"both"``.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application instance.
    domain : str
        The Sphinx domain (only ``'py'`` is handled).
    obj_type : str
        The type of the object.
    contentnode : Element
        The ``desc_content`` node of the object description.

    Examples
    --------
    >>> merge_typehints  # doctest: +ELLIPSIS
    <function merge_typehints at 0x...>
    """
    autodoc_typehints = getattr(app.config, "autodoc_typehints", None)
    if autodoc_typehints not in {"both", "description"}:
        return
    if domain != "py":
        return

    try:
        signature = t.cast("addnodes.desc_signature", contentnode.parent[0])
        if signature["module"]:
            fullname = f"{signature['module']}.{signature['fullname']}"
        else:
            fullname = signature["fullname"]
    except KeyError:
        return

    annotations = app.env.current_document.autodoc_annotations
    if not annotations.get(fullname):
        return

    env = app.env

    field_lists = [n for n in contentnode if isinstance(n, nodes.field_list)]
    if not field_lists:
        field_list = nodes.field_list()
        desc = [n for n in contentnode if isinstance(n, addnodes.desc)]
        if desc:
            index = contentnode.index(desc[0])
            contentnode.insert(index, [field_list])
        else:
            contentnode += field_list
        field_lists.append(field_list)

    for field_list in field_lists:
        # Enhance existing plain-text type fields (e.g. from Napoleon)
        for field in list(field_list.children):
            if not isinstance(field, nodes.field):
                continue
            field_name_text = field[0].astext()
            parts = field_name_text.split()
            if parts[0] in {"type", "rtype"}:
                _enhance_existing_type_field(field, env)

        # Insert missing type/rtype fields with cross-referenced content
        _modify_field_list(field_list, annotations[fullname], obj_type, env)


def _clear_caches(app: Sphinx) -> None:
    """Clear module-level caches at the start of each Sphinx build.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application instance.

    Examples
    --------
    >>> callable(_clear_caches)
    True
    """
    _MODULE_IMPORTS.clear()


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Set up the Sphinx extension.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application instance.

    Returns
    -------
    dict[str, t.Any]
        The extension metadata.

    Examples
    --------
    >>> setup  # doctest: +ELLIPSIS
    <function setup at 0x...>
    """
    import pathlib

    from sphinx_autodoc_typehints_gp._data_defaults import (
        GpAttributeDocumenter,
        GpDataDocumenter,
    )
    from sphinx_autodoc_typehints_gp._default_xref_transform import (
        register as register_default_xref_transform,
    )
    from sphinx_autodoc_typehints_gp._field_xref_transform import (
        register as register_field_xref_transform,
    )
    from sphinx_autodoc_typehints_gp._param_defaults import (
        update_synthetic_defvalues,
    )

    static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(static_dir)

    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/typehints_gp.css")

    app.add_config_value(
        "gp_typehints_curate_param_defaults",
        default=True,
        rebuild="env",
        types=frozenset({bool}),
    )
    app.add_config_value(
        "gp_typehints_curate_data_defaults",
        default=True,
        rebuild="env",
        types=frozenset({bool}),
    )
    app.add_autodocumenter(GpDataDocumenter, override=True)
    app.add_autodocumenter(GpAttributeDocumenter, override=True)
    register_default_xref_transform(app)
    register_field_xref_transform(app)
    app.connect("builder-inited", _clear_caches)
    try:
        app.connect("autodoc-process-docstring", process_docstring)
        app.connect("autodoc-process-signature", record_typehints)
        # Runs after Sphinx's own update_defvalue (which only handles
        # regular methods with readable source). Fills the gap for
        # synthetic dataclass __init__.
        app.connect("autodoc-before-process-signature", update_synthetic_defvalues)
    except ExtensionError as exc:
        if "Unknown event name" not in str(exc):
            raise
    # Priority 499: run before Sphinx's _merge_typehints at 500 so our
    # cross-referenced fields are seen first and the plain-text duplicates
    # are skipped by the built-in handler.
    app.connect("object-description-transform", merge_typehints, priority=499)
    return {
        "version": "0.0.1a35",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
