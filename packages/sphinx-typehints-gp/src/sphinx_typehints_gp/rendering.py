"""Shared annotation rendering helpers for gp-sphinx extensions.

Examples
--------
>>> normalize_annotation_text("list[str] | None", strip_none=True)
'list[str]'
>>> normalize_annotation_text("Literal['open', 'closed']", collapse_literal=True)
"'open', 'closed'"
>>> normalize_type_collection_text((bool, str))
'bool | str'
"""

from __future__ import annotations

import inspect
import re
import typing as t

from docutils import nodes
from sphinx import addnodes
from sphinx.util.typing import stringify_annotation as sphinx_stringify_annotation

from sphinx_typehints_gp.extension import (
    _annotation_to_nodes,
    get_module_imports,
    resolve_annotation_string,
)

if t.TYPE_CHECKING:
    from docutils.nodes import Node
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment


def _downgrade_unresolvable_xrefs(children: list[Node]) -> list[Node]:
    """Replace known-nonresolvable type xrefs with safe inline literals.

    Parameters
    ----------
    children : list[Node]
        Annotation nodes returned by Sphinx's private annotation parser.

    Returns
    -------
    list[Node]
        Nodes safe to insert into arbitrary paragraphs and table cells.

    Examples
    --------
    >>> xref = addnodes.pending_xref("", nodes.Text("None"), reftarget="None")
    >>> _downgrade_unresolvable_xrefs([xref])[0].astext()
    'None'
    """
    result: list[Node] = []
    for child in children:
        if isinstance(child, addnodes.pending_xref) and child.get("reftarget") in {
            "None",
            "NoneType",
        }:
            result.append(nodes.literal("", child.astext()))
            continue
        result.append(child)
    return result


def _strip_optional_none(text: str) -> str:
    """Return *text* without a trailing ``| None`` union member.

    Parameters
    ----------
    text : str
        Normalized annotation text.

    Returns
    -------
    str
        The annotation text with ``None`` removed from a pipe union.

    Examples
    --------
    >>> _strip_optional_none("str | None")
    'str'
    >>> _strip_optional_none("None")
    'None'
    """
    parts = [part.strip() for part in text.split("|")]
    stripped = [part for part in parts if part != "None"]
    if not stripped:
        return text
    return " | ".join(stripped)


def normalize_annotation_text(
    annotation: t.Any,
    *,
    strip_none: bool = False,
    collapse_literal: bool = False,
    module_name: str | None = None,
    aliases: dict[str, str] | None = None,
    qualify_unresolved: bool = False,
) -> str:
    """Return deterministic plain-text annotation content.

    Parameters
    ----------
    annotation : Any
        Annotation object or raw string.
    strip_none : bool
        When ``True``, drop ``None`` from ``X | None`` unions.
    collapse_literal : bool
        When ``True``, collapse ``Literal[...]`` to its member text.
    module_name : str | None
        Module context used when resolving forward-reference strings.
    aliases : dict[str, str] | None
        Explicit import or name aliases used to qualify string annotations.
    qualify_unresolved : bool
        When ``True``, unqualified non-builtin names are resolved relative to
        ``module_name``.

    Returns
    -------
    str
        Stable plain-text annotation.

    Examples
    --------
    >>> normalize_annotation_text(int)
    'int'
    >>> normalize_annotation_text(
    ...     "Session",
    ...     module_name="libtmux.session",
    ...     qualify_unresolved=True,
    ... )
    'libtmux.session.Session'
    >>> normalize_annotation_text(
    ...     "Literal['open', 'closed']",
    ...     collapse_literal=True,
    ... )
    "'open', 'closed'"
    """
    if annotation is inspect.Parameter.empty:
        return ""

    if isinstance(annotation, str):
        text = annotation
    else:
        try:
            text = sphinx_stringify_annotation(annotation, mode="smart")
        except Exception:
            name = getattr(annotation, "__name__", None)
            text = str(name) if isinstance(name, str) else str(annotation)

    text = text.replace("typing.", "").replace("collections.abc.", "")

    if module_name is not None and text:
        alias_map = aliases if aliases is not None else get_module_imports(module_name)
        if alias_map or qualify_unresolved:
            text = resolve_annotation_string(
                text,
                module_name,
                alias_map,
                qualify_unresolved=qualify_unresolved,
            ).replace("~", "")

    if strip_none and text:
        text = _strip_optional_none(text)
    if collapse_literal and text:
        text = re.sub(
            r"(?:t\.)?Literal\[([^\]]+)\]",
            lambda match: match.group(1),
            text,
        )
    return text


def normalize_type_collection_text(
    types: object,
    *,
    default: object = inspect.Parameter.empty,
) -> str:
    """Return a readable type expression for Sphinx config-like metadata.

    Parameters
    ----------
    types : object
        Config-style ``types`` value from ``app.add_config_value()``.
    default : object
        Config default used when no explicit ``types`` are present.

    Returns
    -------
    str
        Human-readable type expression.

    Examples
    --------
    >>> normalize_type_collection_text((bool, str))
    'bool | str'
    >>> normalize_type_collection_text((), default=None)
    'None'
    """
    if isinstance(types, (list, tuple, set, frozenset)) and types:
        names = sorted(
            "None"
            if getattr(item, "__name__", "") == "NoneType"
            else normalize_annotation_text(item)
            for item in t.cast("t.Iterable[t.Any]", types)
        )
        return " | ".join(names)
    if types:
        return normalize_annotation_text(types)
    if default is None:
        return "None"
    if default is inspect.Parameter.empty:
        return ""
    return normalize_annotation_text(type(default))


def render_annotation_nodes(
    annotation: t.Any,
    env: BuildEnvironment,
    *,
    strip_none: bool = False,
    collapse_literal: bool = False,
    module_name: str | None = None,
    aliases: dict[str, str] | None = None,
    qualify_unresolved: bool = False,
) -> list[Node]:
    """Render annotation content into Sphinx/docutils nodes.

    Parameters
    ----------
    annotation : Any
        Annotation object or raw string.
    env : BuildEnvironment
        Sphinx build environment used to create ``pending_xref`` nodes.
    strip_none : bool
        When ``True``, drop ``None`` from ``X | None`` unions.
    collapse_literal : bool
        When ``True``, collapse ``Literal[...]`` to its member text.
    module_name : str | None
        Module context used when resolving forward-reference strings.
    aliases : dict[str, str] | None
        Explicit alias mapping used to qualify annotation names.
    qualify_unresolved : bool
        When ``True``, unqualified non-builtin names are resolved relative to
        ``module_name``.

    Returns
    -------
    list[Node]
        Annotation nodes ready for insertion into a paragraph or table cell.

    Examples
    --------
    >>> render_annotation_nodes  # doctest: +ELLIPSIS
    <function render_annotation_nodes at 0x...>
    """
    text = normalize_annotation_text(
        annotation,
        strip_none=strip_none,
        collapse_literal=collapse_literal,
        module_name=module_name,
        aliases=aliases,
        qualify_unresolved=qualify_unresolved,
    )
    if not text:
        return []
    return _downgrade_unresolvable_xrefs(_annotation_to_nodes(text, env))


def build_annotation_paragraph(
    annotation: t.Any,
    env: BuildEnvironment,
    *,
    strip_none: bool = False,
    collapse_literal: bool = False,
    module_name: str | None = None,
    aliases: dict[str, str] | None = None,
    qualify_unresolved: bool = False,
) -> nodes.paragraph:
    """Return a paragraph containing rendered annotation nodes.

    Parameters
    ----------
    annotation : Any
        Annotation object or raw string.
    env : BuildEnvironment
        Sphinx build environment used to create ``pending_xref`` nodes.
    strip_none : bool
        When ``True``, drop ``None`` from ``X | None`` unions.
    collapse_literal : bool
        When ``True``, collapse ``Literal[...]`` to its member text.
    module_name : str | None
        Module context used when resolving forward-reference strings.
    aliases : dict[str, str] | None
        Explicit alias mapping used to qualify annotation names.
    qualify_unresolved : bool
        When ``True``, unqualified non-builtin names are resolved relative to
        ``module_name``.

    Returns
    -------
    nodes.paragraph
        Paragraph containing the rendered annotation nodes.

    Examples
    --------
    >>> build_annotation_paragraph  # doctest: +ELLIPSIS
    <function build_annotation_paragraph at 0x...>
    """
    paragraph = nodes.paragraph()
    for child in render_annotation_nodes(
        annotation,
        env,
        strip_none=strip_none,
        collapse_literal=collapse_literal,
        module_name=module_name,
        aliases=aliases,
        qualify_unresolved=qualify_unresolved,
    ):
        paragraph += child
    return paragraph


def build_resolved_annotation_paragraph(
    annotation: t.Any,
    app: Sphinx,
    docname: str,
    *,
    strip_none: bool = False,
    collapse_literal: bool = False,
    module_name: str | None = None,
    aliases: dict[str, str] | None = None,
    qualify_unresolved: bool = False,
) -> nodes.paragraph:
    """Return a paragraph with any late-added annotation xrefs resolved.

    Parameters
    ----------
    annotation : Any
        Annotation object or raw string.
    app : Sphinx
        Sphinx application used for environment and builder access.
    docname : str
        Current document name used for reference resolution.
    strip_none : bool
        When ``True``, drop ``None`` from ``X | None`` unions.
    collapse_literal : bool
        When ``True``, collapse ``Literal[...]`` to its member text.
    module_name : str | None
        Module context used when resolving forward-reference strings.
    aliases : dict[str, str] | None
        Explicit alias mapping used to qualify annotation names.
    qualify_unresolved : bool
        When ``True``, unqualified non-builtin names are resolved relative to
        ``module_name``.

    Returns
    -------
    nodes.paragraph
        Paragraph containing resolved annotation nodes.

    Examples
    --------
    >>> build_resolved_annotation_paragraph  # doctest: +ELLIPSIS
    <function build_resolved_annotation_paragraph at 0x...>
    """
    from sphinx.util.docutils import new_document

    paragraph = build_annotation_paragraph(
        annotation,
        app.env,
        strip_none=strip_none,
        collapse_literal=collapse_literal,
        module_name=module_name,
        aliases=aliases,
        qualify_unresolved=qualify_unresolved,
    )
    if not any(
        isinstance(child, addnodes.pending_xref) for child in paragraph.children
    ):
        return paragraph

    temp_doc = new_document("<annotation>")
    temp_para = paragraph.deepcopy()
    temp_doc += temp_para
    app.env.resolve_references(temp_doc, docname, app.builder)
    return t.cast(nodes.paragraph, temp_doc.children[0])
