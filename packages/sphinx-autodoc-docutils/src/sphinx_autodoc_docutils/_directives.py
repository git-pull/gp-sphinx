"""Rendering directives for docutils directive and role documentation."""

from __future__ import annotations

import importlib
import inspect
import typing as t

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective

if t.TYPE_CHECKING:
    from sphinx.util.typing import OptionSpec


def _summary(value: object) -> str:  # object: wraps inspect.getdoc()
    """Return the first summary line for a Python object.

    Examples
    --------
    >>> _summary(Directive)
    'Base class for reStructuredText directives.'
    """
    doc = inspect.getdoc(value) or ""
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _module_members(
    module_name: str,
) -> list[
    tuple[str, object]
]:  # object: inspect.getmembers() returns heterogeneous values
    """Return public members defined directly in a module.

    Examples
    --------
    >>> members = _module_members("sphinx_autodoc_docutils._directives")
    >>> any(name == "AutoDirectiveIndex" for name, _value in members)
    True
    """
    module = importlib.import_module(module_name)
    return [
        (name, value)
        for name, value in inspect.getmembers(module)
        if getattr(value, "__module__", None) == module.__name__
        and not name.startswith("_")
    ]


def _directive_classes(module_name: str) -> list[tuple[str, type[Directive]]]:
    """Return public docutils directive classes in a module.

    Examples
    --------
    >>> directives = _directive_classes("sphinx_autodoc_docutils._directives")
    >>> any(name == "AutoDirectiveIndex" for name, _value in directives)
    True
    """
    results: list[tuple[str, type[Directive]]] = []
    for name, value in _module_members(module_name):
        if inspect.isclass(value) and issubclass(value, Directive):
            results.append((name, value))
    return results


def _role_callables(
    module_name: str,
) -> list[
    tuple[str, object]
]:  # object: roles have monkey-patched attrs; no Protocol fits
    """Return public docutils role callables in a module.

    Examples
    --------
    >>> roles = _role_callables("sphinx_argparse_neo.roles")
    >>> any(name == "cli_option_role" for name, _value in roles)
    True
    """
    results: list[tuple[str, object]] = []
    for name, value in _module_members(module_name):
        if name.endswith("_role") and callable(value):
            results.append((name, value))
    return results


def _registered_name(name: str) -> str:
    """Return the documented name for a directive class or role function.

    Examples
    --------
    >>> _registered_name("AutoDirectiveIndex")
    'autodirective-index'
    >>> _registered_name("cli_option_role")
    'cli-option'
    """
    explicit = {
        "AutoDirective": "autodirective",
        "AutoDirectives": "autodirectives",
        "AutoDirectiveIndex": "autodirective-index",
        "AutoRole": "autorole",
        "AutoRoles": "autoroles",
        "AutoRoleIndex": "autorole-index",
    }
    if name in explicit:
        return explicit[name]
    if name.endswith("_role"):
        return name.removesuffix("_role").replace("_", "-")
    return name.removesuffix("Directive").lower()


def _option_rows(option_spec: OptionSpec | None) -> list[str]:
    """Return table rows describing a directive or role option spec.

    Examples
    --------
    >>> rows = _option_rows({"class": str})
    >>> rows[0]
    '| `class` | `str` |'
    """
    if not isinstance(option_spec, dict) or not option_spec:
        return []
    rows = []
    for name, converter in sorted(option_spec.items()):
        converter_name = getattr(converter, "__name__", type(converter).__name__)
        rows.append(f"| `{name}` | `{converter_name}` |")
    return rows


def _render_blocks(directive: SphinxDirective, markup: str) -> list[nodes.Node]:
    """Parse generated markup through Sphinx when available.

    Examples
    --------
    >>> class DummyState:
    ...     def nested_parse(
    ...         self,
    ...         view_list: StringList,
    ...         offset: int,
    ...         node: nodes.Element,
    ...     ) -> None:
    ...         for line in view_list:
    ...             node += nodes.paragraph("", line)
    >>> class DummyDirective:
    ...     state = DummyState()
    ...     content_offset = 0
    ...     def get_source_info(self) -> tuple[str, int]:
    ...         return ("demo.md", 1)
    >>> rendered = _render_blocks(DummyDirective(), "demo")  # type: ignore[arg-type]
    >>> rendered[0].astext()
    'demo'
    """
    if hasattr(directive, "parse_text_to_nodes"):
        return directive.parse_text_to_nodes(markup)

    source, _line = directive.get_source_info()
    view_list: StringList = StringList()
    for line in markup.splitlines():
        view_list.append(line, source)
    container = nodes.container()
    directive.state.nested_parse(view_list, directive.content_offset, container)
    return [container] if container.children else []


def _directive_markup(
    path: str,
    directive_cls: type[Directive],
    *,
    directive_name: str,
    no_index: bool = False,
) -> str:
    """Return reStructuredText markup documenting one directive class.

    Examples
    --------
    >>> markup = _directive_markup("x.y.MyDirective", Directive, directive_name="my-directive")
    >>> ".. rst:directive:: my-directive" in markup
    True
    """
    lines = [
        f".. rst:directive:: {directive_name}",
        "   :no-index:" if no_index else "",
        "",
        f"   {_summary(directive_cls) or 'Autodocumented directive class.'}",
        "",
        f"   Python path: ``{path}``",
        "",
        f"   Required arguments: ``{directive_cls.required_arguments}``",
        "",
        f"   Optional arguments: ``{directive_cls.optional_arguments}``",
        "",
        f"   Final argument whitespace: ``{directive_cls.final_argument_whitespace}``",
        "",
        f"   Has content: ``{directive_cls.has_content}``",
    ]
    option_rows = _option_rows(getattr(directive_cls, "option_spec", None))
    if option_rows:
        lines.extend(["", "   Options:", ""])
        for row in option_rows:
            option_name, converter_name = row.split("|")[1:3]
            clean_option_name = option_name.strip().strip("`")
            clean_converter_name = converter_name.strip().strip("`")
            lines.extend(
                [
                    f"   .. rst:directive:option:: {clean_option_name}",
                    "      :no-index:" if no_index else "",
                    "",
                    f"      Validator: ``{clean_converter_name}``.",
                    "",
                ]
            )
    return "\n".join(lines)


def _role_markup(
    path: str,
    role_name: str,
    role_fn: object,  # object: accesses .options/.content via getattr; Protocol impractical
    *,
    no_index: bool = False,
) -> str:
    """Return reStructuredText markup documenting one role callable.

    Examples
    --------
    >>> def demo_role(*args: object, **kwargs: object) -> tuple[list[object], list[object]]:
    ...     return [], []
    >>> demo_role.options = {"class": str}
    >>> markup = _role_markup("demo.demo_role", "demo", demo_role)
    >>> ".. rst:role:: demo" in markup
    True
    """
    lines = [
        f".. rst:role:: {role_name}",
        "   :no-index:" if no_index else "",
        "",
        f"   {_summary(role_fn) or 'Autodocumented role callable.'}",
        "",
        f"   Python path: ``{path}``",
    ]
    option_rows = _option_rows(getattr(role_fn, "options", None))
    if option_rows:
        lines.extend(["", "   Options:", ""])
        for row in option_rows:
            option_name, converter_name = row.split("|")[1:3]
            clean_option_name = option_name.strip().strip("`")
            clean_converter_name = converter_name.strip().strip("`")
            lines.append(f"   - ``{clean_option_name}``: ``{clean_converter_name}``")
    content_value = getattr(role_fn, "content", None)
    if content_value is not None:
        lines.extend(["", f"   Accepts role content: ``{content_value}``"])
    return "\n".join(lines)


def _index_markup(heading: str, rows: list[tuple[str, str, str]]) -> str:
    """Return a reStructuredText summary table for autodocumented objects.

    Examples
    --------
    >>> markup = _index_markup("Demo", [("x", "p.x", "summary")])
    >>> ".. list-table::" in markup
    True
    """
    if not rows:
        return ""
    lines = [
        f".. rubric:: {heading}",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        "",
        "   * - Name",
        "     - Python path",
        "     - Summary",
    ]
    for name, path, summary in rows:
        lines.extend(
            [
                f"   * - ``{name}``",
                f"     - ``{path}``",
                f"     - {summary}",
            ]
        )
    return "\n".join(lines)


class AutoDirective(SphinxDirective):
    """Render documentation for a single directive class."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        path = self.arguments[0]
        module_name, _, attr_name = path.rpartition(".")
        directive_cls = getattr(importlib.import_module(module_name), attr_name)
        return _render_blocks(
            self,
            _directive_markup(
                path,
                directive_cls,
                directive_name=_registered_name(attr_name),
                no_index="no-index" in self.options,
            ),
        )


class AutoDirectives(SphinxDirective):
    """Render documentation for every directive class in a module."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        module_name = self.arguments[0]
        markup = "\n\n".join(
            _directive_markup(
                f"{module_name}.{name}",
                directive_cls,
                directive_name=_registered_name(name),
                no_index="no-index" in self.options,
            )
            for name, directive_cls in _directive_classes(module_name)
        )
        return _render_blocks(self, markup) if markup else []


class AutoDirectiveIndex(SphinxDirective):
    """Generate a summary index for all directives in a module."""

    required_arguments = 1
    has_content = False

    def run(self) -> list[nodes.Node]:
        module_name = self.arguments[0]
        rows = [
            (_registered_name(name), f"{module_name}.{name}", _summary(directive_cls))
            for name, directive_cls in _directive_classes(module_name)
        ]
        markup = _index_markup("Directive Index", rows)
        return _render_blocks(self, markup) if markup else []


class AutoRole(SphinxDirective):
    """Render documentation for a single role callable."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        path = self.arguments[0]
        module_name, _, attr_name = path.rpartition(".")
        role_fn = getattr(importlib.import_module(module_name), attr_name)
        role_name = _registered_name(attr_name)
        return _render_blocks(
            self,
            _role_markup(
                path,
                role_name,
                role_fn,
                no_index="no-index" in self.options,
            ),
        )


class AutoRoles(SphinxDirective):
    """Render documentation for every role callable in a module."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        module_name = self.arguments[0]
        markup = "\n\n".join(
            _role_markup(
                f"{module_name}.{name}",
                _registered_name(name),
                role_fn,
                no_index="no-index" in self.options,
            )
            for name, role_fn in _role_callables(module_name)
        )
        return _render_blocks(self, markup) if markup else []


class AutoRoleIndex(SphinxDirective):
    """Generate a summary index for all roles in a module."""

    required_arguments = 1
    has_content = False

    def run(self) -> list[nodes.Node]:
        module_name = self.arguments[0]
        rows = [
            (
                _registered_name(name),
                f"{module_name}.{name}",
                _summary(role_fn),
            )
            for name, role_fn in _role_callables(module_name)
        ]
        markup = _index_markup("Role Index", rows)
        return _render_blocks(self, markup) if markup else []
