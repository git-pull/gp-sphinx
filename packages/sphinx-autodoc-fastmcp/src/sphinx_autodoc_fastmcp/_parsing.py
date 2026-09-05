"""Docstring and signature parsing for FastMCP tools."""

from __future__ import annotations

import ast
import inspect
import re
import typing as t

from docutils import nodes

from sphinx_autodoc_fastmcp._models import ParamInfo
from sphinx_autodoc_typehints_gp import classify_annotation_display


def parse_numpy_params(docstring: str) -> dict[str, str]:
    """Extract parameter descriptions from NumPy-style docstring.

    Parameters
    ----------
    docstring : str
        Full docstring text.

    Returns
    -------
    dict[str, str]
        Mapping parameter name to description.

    Examples
    --------
    >>> parse_numpy_params("")
    {}
    """
    params: dict[str, str] = {}
    if not docstring:
        return params

    lines = docstring.split("\n")
    in_params = False
    current_param: str | None = None
    current_desc: list[str] = []

    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if stripped == "Parameters":
            in_params = True
            continue
        if in_params and stripped.startswith("---"):
            continue
        if in_params and stripped in (
            "Returns",
            "Raises",
            "Notes",
            "Examples",
            "See Also",
        ):
            if current_param:
                params[current_param] = " ".join(current_desc).strip()
            break
        if in_params and not stripped:
            continue

        if in_params:
            param_match = re.match(r"^(\w+)\s*:", stripped)
            if param_match and indent == 0:
                if current_param:
                    params[current_param] = " ".join(current_desc).strip()
                current_param = param_match.group(1)
                current_desc = []
            elif current_param and indent > 0:
                current_desc.append(stripped)

    if current_param:
        params[current_param] = " ".join(current_desc).strip()

    return params


def first_paragraph(docstring: str) -> str:
    """Extract the first paragraph from a docstring.

    Examples
    --------
    >>> first_paragraph("Hello.")
    'Hello.'
    """
    if not docstring:
        return ""
    paragraphs = docstring.strip().split("\n\n")
    return paragraphs[0].strip().replace("\n", " ")


def _strip_annotated(annotation: t.Any) -> t.Any:
    """Reduce ``Annotated[X, ...]`` to ``X``, in object or source-string form.

    Under PEP 563 an annotation arrives as the author's source text, which is
    the best display available -- except when it carries ``Annotated``
    metadata, because that metadata is code.

    Examples
    --------
    An annotation without metadata is its own best display:

    >>> _strip_annotated("list[str] | None")
    'list[str] | None'

    Metadata is dropped, whether the annotation arrives as source text or as a
    resolved object:

    >>> _strip_annotated("t.Annotated[list[str], Field(description='x')]")
    'list[str]'
    >>> import typing
    >>> _strip_annotated(typing.Annotated[int, "meta"])
    <class 'int'>

    A description built at import time would otherwise reach the page as the
    call that produced it:

    >>> _strip_annotated("Annotated[str, Field(description=f'{summary()}')]")
    'str'

    Text that does not parse is returned untouched rather than raising:

    >>> _strip_annotated("Annotated[str,")
    'Annotated[str,'
    """
    if isinstance(annotation, str):
        if "Annotated[" not in annotation:
            return annotation
        try:
            node = ast.parse(annotation, mode="eval").body
        except SyntaxError:
            return annotation
        if isinstance(node, ast.Subscript):
            target = node.value
            name = (
                target.attr
                if isinstance(target, ast.Attribute)
                else getattr(target, "id", "")
            )
            if name == "Annotated":
                sl = node.slice
                if isinstance(sl, ast.Tuple) and sl.elts:
                    return ast.unparse(sl.elts[0])
        return annotation
    if t.get_origin(annotation) is t.Annotated:
        return t.get_args(annotation)[0]
    return annotation


def extract_params(func: t.Callable[..., t.Any]) -> list[ParamInfo]:
    """Extract parameter info from function signature and docstring."""
    sig = inspect.signature(func)
    doc_params = parse_numpy_params(func.__doc__ or "")
    params: list[ParamInfo] = []

    for name, param in sig.parameters.items():
        is_optional = param.default != inspect.Parameter.empty
        display = classify_annotation_display(
            _strip_annotated(param.annotation),
            strip_none=is_optional,
        )

        if is_optional:
            if param.default is None:
                default_str = "None"
            elif isinstance(param.default, bool):
                default_str = str(param.default)
            elif isinstance(param.default, str):
                default_str = repr(param.default)
            else:
                default_str = str(param.default)
            required = False
        else:
            default_str = ""
            required = True

        params.append(
            ParamInfo(
                name=name,
                type_str=display.text,
                required=required,
                default=default_str,
                description=doc_params.get(name, ""),
            ),
        )

    return params


def make_literal(text: str) -> nodes.literal:
    """Create an inline code literal node."""
    return nodes.literal("", text)


def make_para(*children: nodes.Node | str) -> nodes.paragraph:
    """Create a paragraph from mixed text and node children."""
    para = nodes.paragraph("")
    for child in children:
        if isinstance(child, str):
            para += nodes.Text(child)
        else:
            para += child
    return para


def parse_rst_inline(
    text: str,
    state: t.Any,
    lineno: int,
) -> nodes.paragraph:
    """Parse RST inline markup into a paragraph node."""
    parsed_nodes, _messages = state.inline_text(text, lineno)
    para = nodes.paragraph("")
    para += parsed_nodes
    return para


def make_table(
    headers: list[str],
    rows: list[list[str | nodes.Node]],
    col_widths: list[int] | None = None,
) -> nodes.table:
    """Build a docutils table node from headers and rows.

    Examples
    --------
    >>> t = make_table(["A"], [["x"]])
    >>> isinstance(t, nodes.table)
    True
    """
    ncols = len(headers)
    if col_widths is None:
        col_widths = [100 // ncols] * ncols

    table = nodes.table("")
    tgroup = nodes.tgroup("", cols=ncols)
    table += tgroup

    for width in col_widths:
        tgroup += nodes.colspec("", colwidth=width)

    thead = nodes.thead("")
    header_row = nodes.row("")
    for header in headers:
        entry = nodes.entry("")
        entry += nodes.paragraph("", header)
        header_row += entry
    thead += header_row
    tgroup += thead

    tbody = nodes.tbody("")
    for row_data in rows:
        row = nodes.row("")
        for cell in row_data:
            entry = nodes.entry("")
            if isinstance(cell, nodes.Node):
                entry += cell
            else:
                entry += nodes.paragraph("", str(cell))
            row += entry
        tbody += row
    tgroup += tbody

    return table
