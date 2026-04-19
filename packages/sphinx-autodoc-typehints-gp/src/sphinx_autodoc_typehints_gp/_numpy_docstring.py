"""NumPy docstring preprocessor replacing ``sphinx.ext.napoleon``.

Converts NumPy-style section-based docstrings into RST field lists during
``autodoc-process-docstring``, eliminating the need for
``sphinx.ext.napoleon``.

The parser handles: Parameters, Returns, Raises, Yields, Receives,
Examples, Notes, See Also, Attributes, References, and admonition sections
(Warning, Note, Caution, etc.).

Type cross-referencing is NOT done here — that is handled by the companion
``merge_typehints`` doctree transform in ``extension.py`` which converts
plain-text type fields into ``pending_xref`` nodes.

Examples
--------
>>> lines = [
...     "Short summary.",
...     "",
...     "Parameters",
...     "----------",
...     "x : int",
...     "    The value.",
... ]
>>> result = process_numpy_docstring(lines)
>>> ":param x: The value." in result
True
>>> ":type x: int" in result
True
"""

from __future__ import annotations

import collections
import re
import typing as t

_NUMPY_UNDERLINE_RE = re.compile(r"^[=\-`:'\"~^_*+#<>]{2,}\s*$")
_ROLE_RE = re.compile(r":[a-zA-Z][a-zA-Z0-9_.-]*:`([^`]+)`")
_TODO_DIRECTIVE_RE = re.compile(r"^\.\.\s+todo\s*::")

_XREF_OR_CODE_RE = re.compile(
    r"((?::(?:[a-zA-Z0-9]+[\-_+:.])*[a-zA-Z0-9]+:`.+?`)|"
    r"(?:``.+?``)|"
    r"(?::meta .+:.*)|"
    r"(?:`.+?\s*(?<!\x00)<.*?>`))"
)
_SINGLE_COLON_RE = re.compile(r"(?<!:):(?!:)")
_SA_NAME_RE = re.compile(r"\s*(?::(\S+):`([^`]+)`|([^\s,]+))\s*")
_BULLET_LIST_RE = re.compile(r"^(\*|\+|\-)(\s+\S|\s*$)")
_ENUM_LIST_RE = re.compile(
    r"^(?P<paren>\()?"
    r"(\d+|#|[ivxlcdm]+|[IVXLCDM]+|[a-zA-Z])"
    r"(?(paren)\)|\.)(\s+\S|\s*$)"
)

_PARAM_NAMES = frozenset(
    {"parameters", "params", "args", "arguments", "other parameters"}
)
_KEYWORD_NAMES = frozenset({"keyword arguments", "keyword args"})
_RETURN_NAMES = frozenset({"returns", "return"})
_RAISE_NAMES = frozenset({"raises", "raise"})
_YIELD_NAMES = frozenset({"yields", "yield"})
_RECEIVE_NAMES = frozenset({"receives", "receive"})
_ATTRIBUTE_NAMES = frozenset({"attributes"})
_EXAMPLE_NAMES = frozenset({"examples", "example"})
_NOTE_NAMES = frozenset({"notes"})
_REFERENCE_NAMES = frozenset({"references"})
_SEE_ALSO_NAMES = frozenset({"see also"})
_METHOD_NAMES = frozenset({"methods"})
_ADMONITION_MAP: dict[str, str] = {
    "warning": "warning",
    "warnings": "warning",
    "caution": "caution",
    "danger": "danger",
    "error": "error",
    "hint": "hint",
    "important": "important",
    "note": "note",
    "tip": "tip",
    "todo": "todo",
    "attention": "attention",
}
_ALL_SECTIONS = (
    _PARAM_NAMES
    | _KEYWORD_NAMES
    | _RETURN_NAMES
    | _RAISE_NAMES
    | _YIELD_NAMES
    | _RECEIVE_NAMES
    | _ATTRIBUTE_NAMES
    | _EXAMPLE_NAMES
    | _NOTE_NAMES
    | _REFERENCE_NAMES
    | _SEE_ALSO_NAMES
    | _METHOD_NAMES
    | set(_ADMONITION_MAP)
)


def process_numpy_docstring(lines: list[str]) -> list[str]:
    """Convert NumPy-style docstring lines to RST field lists.

    Parameters
    ----------
    lines : list[str]
        Raw docstring lines from autodoc.

    Returns
    -------
    list[str]
        Processed lines with NumPy sections converted to RST.

    Examples
    --------
    >>> result = process_numpy_docstring([
    ...     "Summary line.",
    ...     "",
    ...     "Parameters",
    ...     "----------",
    ...     "x : int",
    ...     "    The x value.",
    ...     "y : str",
    ...     "    The y value.",
    ... ])
    >>> ":param x: The x value." in result
    True
    >>> ":type x: int" in result
    True
    >>> ":param y: The y value." in result
    True

    >>> result = process_numpy_docstring(["No sections here."])
    >>> result
    ['No sections here.']
    """
    return _NumpyParser(lines).parse()


def _partition_on_colon(line: str) -> tuple[str, str, str]:
    """Split *line* on the first bare colon outside cross-refs and code.

    Parameters
    ----------
    line : str
        A single docstring line.

    Returns
    -------
    tuple[str, str, str]
        ``(before, colon, after)`` — *colon* is ``':'`` when found,
        otherwise all three are ``('', '', '')``.

    Examples
    --------
    >>> _partition_on_colon("name : int")
    ('name', ':', 'int')

    >>> _partition_on_colon("name")
    ('name', '', '')

    >>> _partition_on_colon(":class:`Foo` : bar")
    (':class:`Foo`', ':', 'bar')
    """
    before: list[str] = []
    after: list[str] = []
    colon = ""
    found = False
    for i, source in enumerate(_XREF_OR_CODE_RE.split(line)):
        if found:
            after.append(source)
        else:
            m = _SINGLE_COLON_RE.search(source)
            if (i % 2) == 0 and m:
                found = True
                colon = source[m.start() : m.end()]
                before.append(source[: m.start()])
                after.append(source[m.end() :])
            else:
                before.append(source)
    return "".join(before).strip(), colon, "".join(after).strip()


def _escape_args_and_kwargs(name: str) -> str:
    r"""Escape ``*`` and ``**`` prefixes for RST compatibility.

    Parameters
    ----------
    name : str
        Parameter name, possibly prefixed with ``*`` or ``**``.

    Returns
    -------
    str
        Escaped name.

    Examples
    --------
    >>> _escape_args_and_kwargs("args")
    'args'
    >>> _escape_args_and_kwargs("*args")
    '\\*args'
    >>> _escape_args_and_kwargs("**kwargs")
    '\\*\\*kwargs'
    """
    if name.startswith("**"):
        return rf"\*\*{name[2:]}"
    if name.startswith("*"):
        return rf"\*{name[1:]}"
    return name


def _get_indent(line: str) -> int:
    """Return the number of leading whitespace characters.

    Examples
    --------
    >>> _get_indent("    hello")
    4
    >>> _get_indent("hello")
    0
    >>> _get_indent("")
    0
    """
    for i, ch in enumerate(line):
        if not ch.isspace():
            return i
    return len(line)


def _is_indented(line: str, indent: int = 1) -> bool:
    """Check whether *line* is indented at least *indent* characters.

    Examples
    --------
    >>> _is_indented("  x", 2)
    True
    >>> _is_indented(" x", 2)
    False
    """
    for i, ch in enumerate(line):
        if i >= indent:
            return True
        if not ch.isspace():
            return False
    return False


def _dedent(lines: list[str]) -> list[str]:
    """Remove common leading whitespace from *lines*.

    Examples
    --------
    >>> _dedent(["    a", "    b"])
    ['a', 'b']
    >>> _dedent(["  a", "    b"])
    ['a', '  b']
    """
    min_indent: int | None = None
    for line in lines:
        if line:
            ind = _get_indent(line)
            if min_indent is None or ind < min_indent:
                min_indent = ind
    n = min_indent or 0
    return [line[n:] for line in lines]


def _strip_empty(lines: list[str]) -> list[str]:
    """Strip leading and trailing empty lines.

    Examples
    --------
    >>> _strip_empty(["", "a", "b", ""])
    ['a', 'b']
    """
    start = 0
    for i, line in enumerate(lines):
        if line:
            start = i
            break
    else:
        return []
    end = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i]:
            end = i + 1
            break
    return lines[start:end]


def _indent(lines: list[str], n: int = 4) -> list[str]:
    """Indent every line by *n* spaces.

    Examples
    --------
    >>> _indent(["a", "b"], 3)
    ['   a', '   b']
    """
    pad = " " * n
    return [pad + line for line in lines]


def _strip_roles(s: str) -> str:
    """Strip RST inline role markup, returning just the target text.

    Examples
    --------
    >>> _strip_roles(":exc:`ValueError`")
    'ValueError'
    >>> _strip_roles(":exc:`exc.Foo`, :exc:`exc.Bar`")
    'exc.Foo, exc.Bar'
    >>> _strip_roles("plain")
    'plain'
    """
    return _ROLE_RE.sub(r"\1", s)


def _filter_invisible_directives(lines: list[str]) -> list[str]:
    """Remove ``.. todo::`` directives and their indented body from *lines*.

    Examples
    --------
    >>> _filter_invisible_directives([".. todo::", "", "    assure it works.", "text"])
    ['text']
    >>> _filter_invisible_directives(["keep this", ".. todo::", "    body"])
    ['keep this']
    """
    result: list[str] = []
    skip_indent: int | None = None
    for line in lines:
        if skip_indent is not None:
            if not line or _is_indented(line, skip_indent + 1):
                continue
            skip_indent = None
        if _TODO_DIRECTIVE_RE.match(line.lstrip()):
            skip_indent = _get_indent(line)
            continue
        result.append(line)
    return result


def _is_list(lines: list[str]) -> bool:
    """Return whether *lines* starts with a bullet or enumerated list."""
    if not lines:
        return False
    if _BULLET_LIST_RE.match(lines[0]):
        return True
    if _ENUM_LIST_RE.match(lines[0]):
        return True
    if len(lines) < 2 or lines[0].endswith("::"):
        return False
    indent = _get_indent(lines[0])
    next_indent = indent
    for line in lines[1:]:
        if line:
            next_indent = _get_indent(line)
            break
    return next_indent > indent


def _fix_field_desc(desc: list[str]) -> list[str]:
    """Prepend a blank line when *desc* starts a list or literal block."""
    if _is_list(desc):
        return ["", *desc]
    if desc[0].endswith("::"):
        block = desc[1:]
        indent = _get_indent(desc[0])
        block_indent = _get_indent(block[0]) if block else indent
        if block_indent > indent:
            return ["", *desc]
        return ["", desc[0], *_indent(block, 4)]
    return desc


def _format_block(prefix: str, lines: list[str]) -> list[str]:
    """Format *lines* with *prefix* on the first line, padding thereafter.

    Examples
    --------
    >>> _format_block(":param x: ", ["Desc", "continued."])
    [':param x: Desc', '          continued.']
    """
    if not lines:
        return [prefix]
    padding = " " * len(prefix)
    result: list[str] = []
    for i, line in enumerate(lines):
        if i == 0:
            result.append((prefix + line).rstrip())
        elif line:
            result.append(padding + line)
        else:
            result.append("")
    return result


def _format_field(name: str, type_: str, desc: list[str]) -> list[str]:
    """Format a single field entry as ``**name** (*type*) -- desc``.

    Used for multi-value returns, yields, and warns sections where
    individual ``:rtype:`` fields are not appropriate.

    Examples
    --------
    >>> _format_field("x", "int", ["The value."])
    ['**x** (*int*) -- The value.']

    >>> _format_field("", "bool", ["True if ok."])
    ['*bool* -- True if ok.']
    """
    desc = _strip_empty(desc)
    has_desc = any(desc)
    separator = " -- " if has_desc else ""
    if name:
        if type_:
            if "`" in type_:
                header = f"**{name}** ({type_}){separator}"
            else:
                header = f"**{name}** (*{type_}*){separator}"
        else:
            header = f"**{name}**{separator}"
    elif type_:
        header = f"{type_}{separator}" if "`" in type_ else f"*{type_}*{separator}"
    else:
        header = ""

    if has_desc:
        desc = _fix_field_desc(desc)
        if desc[0]:
            return [header + desc[0], *desc[1:]]
        return [header, *desc]
    return [header]


def _parse_sa_item(text: str) -> tuple[str, str | None]:
    """Extract a name and optional Sphinx role from a See Also entry.

    Matches ``:role:`name``` (returning the role) or a plain ``name``
    (returning ``None`` for the role).

    Parameters
    ----------
    text : str
        The text to parse, e.g. ``":func:`my_func`"`` or ``"my_func"``.

    Returns
    -------
    tuple[str, str | None]
        ``(name, role)`` where *role* is ``None`` for plain names.

    Examples
    --------
    >>> _parse_sa_item("my_func")
    ('my_func', None)
    >>> _parse_sa_item(":func:`my_func`")
    ('my_func', 'func')
    >>> _parse_sa_item(":py:meth:`Widget.run`")
    ('Widget.run', 'py:meth')
    >>> _parse_sa_item("")
    ('', None)
    """
    m = _SA_NAME_RE.match(text.strip())
    if not m:
        return text.strip(), None
    role, role_name, plain_name = m.group(1), m.group(2), m.group(3)
    if role is not None:
        return role_name, role
    return plain_name, None


class _NumpyParser:
    """Line-based NumPy docstring parser.

    Consumes docstring lines from a deque, detecting NumPy section
    headers and dispatching to section-specific formatters that produce
    RST output.
    """

    __slots__ = ("_in_section", "_lines", "_section_indent")

    def __init__(self, lines: t.Sequence[str]) -> None:
        self._lines: collections.deque[str] = collections.deque(
            line.rstrip() for line in lines
        )
        self._in_section = False
        self._section_indent = 0

    # -- public API --

    def parse(self) -> list[str]:
        """Parse the docstring and return RST lines."""
        result = self._consume_empty()
        first_block = True
        while self._lines:
            if self._is_section_header():
                section = self._consume_section_header()
                self._in_section = True
                self._section_indent = self._current_indent()
                try:
                    result.extend(self._dispatch(section.lower()))
                finally:
                    self._in_section = False
                    self._section_indent = 0
                first_block = False
            elif first_block:
                result.extend(self._consume_contiguous())
                result.extend(self._consume_empty())
                first_block = False
            else:
                result.extend(self._consume_to_next_section())
        return result

    # -- line access --

    def _peek(self, n: int = 0) -> str:
        if n < len(self._lines):
            return self._lines[n]
        return ""

    def _next(self) -> str:
        return self._lines.popleft()

    # -- detection --

    def _is_section_header(self) -> bool:
        section = self._peek(0).strip().lower()
        underline = self._peek(1)
        return bool(
            section in _ALL_SECTIONS
            and underline
            and _NUMPY_UNDERLINE_RE.match(underline)
        )

    def _is_section_break(self) -> bool:
        line1 = self._peek(0)
        line2 = self._peek(1)
        return (
            not self._lines
            or self._is_section_header()
            or (not line1 and not line2)
            or (
                self._in_section
                and bool(line1)
                and not _is_indented(line1, self._section_indent)
            )
        )

    def _current_indent(self, peek_ahead: int = 0) -> int:
        idx = peek_ahead
        while idx < len(self._lines):
            line = self._lines[idx]
            if line:
                return _get_indent(line)
            idx += 1
        return 0

    # -- consumers --

    def _consume_section_header(self) -> str:
        section = self._next()
        self._next()  # underline
        return section.strip()

    def _consume_empty(self) -> list[str]:
        result: list[str] = []
        while self._lines and not self._peek(0):
            result.append(self._next())
        return result

    def _consume_contiguous(self) -> list[str]:
        result: list[str] = []
        while self._lines and self._peek(0) and not self._is_section_header():
            result.append(self._next())
        return result

    def _consume_to_next_section(self) -> list[str]:
        self._consume_empty()
        result: list[str] = []
        while not self._is_section_break():
            result.append(self._next())
        result.extend(self._consume_empty())
        return result

    def _consume_indented_block(self, indent: int = 1) -> list[str]:
        result: list[str] = []
        while not self._is_section_break() and (
            not self._peek(0) or _is_indented(self._peek(0), indent)
        ):
            result.append(self._next())
        return result

    def _consume_field(
        self,
        parse_type: bool = True,
        prefer_type: bool = False,
    ) -> tuple[str, str, list[str]]:
        line = self._next()
        if parse_type:
            name, _, type_ = _partition_on_colon(line)
        else:
            name, type_ = line, ""
        name = name.strip()
        type_ = type_.strip()

        if ", " in name:
            name = ", ".join(
                _escape_args_and_kwargs(n.strip()) for n in name.split(", ")
            )
        else:
            name = _escape_args_and_kwargs(name)

        if prefer_type and not type_:
            type_, name = name, type_

        indent = _get_indent(line) + 1
        desc = _dedent(self._consume_indented_block(indent))
        return name, type_, desc

    def _consume_fields(
        self,
        parse_type: bool = True,
        prefer_type: bool = False,
        multiple: bool = False,
    ) -> list[tuple[str, str, list[str]]]:
        self._consume_empty()
        fields: list[tuple[str, str, list[str]]] = []
        while not self._is_section_break():
            name, type_, desc = self._consume_field(parse_type, prefer_type)
            if multiple and name:
                fields.extend((n.strip(), type_, desc) for n in name.split(","))
            elif name or type_ or desc:
                fields.append((name, type_, desc))
        return fields

    # -- dispatch --

    def _dispatch(self, section: str) -> list[str]:
        if section in _PARAM_NAMES:
            return self._fmt_params()
        if section in _KEYWORD_NAMES:
            return self._fmt_params(field_role="keyword", type_role="kwtype")
        if section in _RETURN_NAMES:
            return self._fmt_returns()
        if section in _RAISE_NAMES:
            return self._fmt_raises()
        if section in _YIELD_NAMES:
            return self._fmt_fields("Yields")
        if section in _RECEIVE_NAMES:
            return self._fmt_params()
        if section in _ATTRIBUTE_NAMES:
            return self._fmt_attributes()
        if section in _EXAMPLE_NAMES:
            label = "Example" if section == "example" else "Examples"
            return self._fmt_generic(label)
        if section in _NOTE_NAMES:
            return self._fmt_generic("Notes")
        if section in _REFERENCE_NAMES:
            return self._fmt_generic("References")
        if section in _SEE_ALSO_NAMES:
            return self._fmt_see_also()
        if section in _METHOD_NAMES:
            return self._fmt_methods()
        if section in _ADMONITION_MAP:
            return self._fmt_admonition(_ADMONITION_MAP[section])
        return self._fmt_generic(section.title())

    # -- section formatters --

    def _fmt_params(
        self, field_role: str = "param", type_role: str = "type"
    ) -> list[str]:
        fields = self._consume_fields(multiple=True)
        lines: list[str] = []
        for name, type_, desc in fields:
            desc = _strip_empty(desc)
            if any(desc):
                desc = _fix_field_desc(desc)
                lines.extend(_format_block(f":{field_role} {name}: ", desc))
            else:
                lines.append(f":{field_role} {name}:")
            if type_:
                lines.append(f":{type_role} {name}: {type_}")
        if lines:
            lines.append("")
        return lines

    def _fmt_returns(self) -> list[str]:
        fields = self._consume_fields(prefer_type=True)
        multi = len(fields) > 1
        lines: list[str] = []
        for name, type_, desc in fields:
            if multi:
                field = _format_field(name, type_, desc)
                if lines:
                    lines.extend(_format_block("          * ", field))
                else:
                    lines.extend(_format_block(":returns: * ", field))
            else:
                field = _format_field(name, "", desc)
                if any(field):
                    lines.extend(_format_block(":returns: ", field))
                if type_:
                    lines.extend([f":rtype: {type_}", ""])
        if lines and lines[-1]:
            lines.append("")
        return lines

    def _fmt_raises(self) -> list[str]:
        fields = self._consume_fields(parse_type=False, prefer_type=True)
        lines: list[str] = []
        for _name, type_, desc in fields:
            type_ = _strip_roles(type_)
            exc_types = [
                part.strip().rstrip(",")
                for part in type_.split(",")
                if part.strip().rstrip(",")
            ]
            if not exc_types:
                exc_types = [""]
            desc = _strip_empty(desc)
            for exc_type in exc_types:
                type_str = f" {exc_type}" if exc_type else ""
                if any(desc):
                    lines.extend(_format_block(f":raises{type_str}: ", desc))
                else:
                    lines.append(f":raises{type_str}:")
        if lines:
            lines.append("")
        return lines

    def _fmt_fields(self, label: str) -> list[str]:
        fields = self._consume_fields(prefer_type=True)
        if not fields:
            return []
        prefix = f":{label}:"
        padding = " " * len(prefix)
        multi = len(fields) > 1
        lines: list[str] = []
        for name, type_, desc in fields:
            field = _format_field(name, type_, desc)
            if multi:
                if lines:
                    lines.extend(_format_block(f"{padding} * ", field))
                else:
                    lines.extend(_format_block(f"{prefix} * ", field))
            else:
                lines.extend(_format_block(f"{prefix} ", field))
        if lines and lines[-1]:
            lines.append("")
        return lines

    def _fmt_attributes(self) -> list[str]:
        lines: list[str] = []
        for name, type_, desc in self._consume_fields():
            lines.append(f".. attribute:: {name}")
            lines.append("")
            fields = _format_field("", "", desc)
            lines.extend(_indent(fields, 3))
            if type_:
                lines.append("")
                lines.extend(_indent([f":type: {type_}"], 3))
            lines.append("")
        return lines

    def _fmt_methods(self) -> list[str]:
        lines: list[str] = []
        for name, _type, desc in self._consume_fields(parse_type=False):
            lines.append(f".. method:: {name}")
            if desc:
                lines.extend(["", *_indent(desc, 3)])
            lines.append("")
        return lines

    def _fmt_generic(self, label: str) -> list[str]:
        raw = _strip_empty(self._consume_to_next_section())
        raw = _dedent(raw)
        raw = _strip_empty(_filter_invisible_directives(raw))
        header = f".. rubric:: {label}"
        if raw:
            return [header, "", *raw, ""]
        return []

    def _fmt_admonition(self, directive: str) -> list[str]:
        raw = _strip_empty(self._consume_to_next_section())
        if len(raw) == 1:
            return [f".. {directive}:: {raw[0].strip()}", ""]
        if raw:
            raw = _indent(_dedent(raw), 3)
            return [f".. {directive}::", "", *raw, ""]
        return [f".. {directive}::", ""]

    def _fmt_see_also(self) -> list[str]:
        lines = self._consume_to_next_section()
        items: list[tuple[str, list[str], str | None]] = []
        current_name: str | None = None
        current_desc: list[str] = []

        def _push_item(name: str | None, desc: list[str]) -> None:
            if not name:
                return
            parsed_name, role = _parse_sa_item(name)
            items.append((parsed_name, desc.copy(), role))

        for line in lines:
            if not line.strip():
                continue
            if not line.startswith(" "):
                _push_item(current_name, current_desc)
                current_desc = []
                current_name = None
                if "," in line:
                    for part in line.split(","):
                        if part.strip():
                            _push_item(part, [])
                elif " : " in line:
                    _sa_name, _, _sa_desc = line.partition(" : ")
                    current_name = _sa_name.strip()
                    current_desc = [_sa_desc.strip()] if _sa_desc.strip() else []
                else:
                    current_name = line.strip()
            elif current_name is not None:
                current_desc.append(line.strip())

        _push_item(current_name, current_desc)

        if not items:
            return []

        body: list[str] = []
        last_had_desc = True
        for item_name, item_desc, item_role in items:
            if item_role:
                link = f":{item_role}:`{item_name}`"
            else:
                link = f":py:obj:`{item_name}`"
            if item_desc or last_had_desc:
                body.append("")
                body.append(link)
            else:
                body[-1] += f", {link}"
            if item_desc:
                body.extend(_indent([" ".join(item_desc)], 3))
                last_had_desc = True
            else:
                last_had_desc = False
        body.append("")

        raw = _indent(_dedent(body), 3)
        return [".. seealso::", "", *raw, ""]
