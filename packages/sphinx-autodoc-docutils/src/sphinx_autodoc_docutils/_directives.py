"""Rendering directives for docutils directive and role documentation."""

from __future__ import annotations

import functools
import importlib
import inspect
import logging
import typing as t

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx import addnodes
from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_docutils._badges import build_kind_badge_group
from sphinx_ux_autodoc_layout import (
    API,
    ApiFactRow,
    build_api_facts_section,
    build_api_table_section,
    build_chip_paragraph,
    build_linked_literal,
    inject_signature_slots,
    iter_desc_nodes,
    parse_generated_markup,
)

if t.TYPE_CHECKING:
    from sphinx.util.typing import OptionSpec

logger = logging.getLogger(__name__)


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
    >>> any(name == "AutoDirectives" for name, _value in members)
    True
    """
    module = importlib.import_module(module_name)
    return [
        (name, value)
        for name, value in inspect.getmembers(module)
        if getattr(value, "__module__", None) == module.__name__
        and not name.startswith("_")
    ]


class SetupRecorder:
    """Record ``app.add_*`` calls made during a Sphinx extension's ``setup()``.

    Public discovery primitive shared with other workspace consumers
    (notably ``docs/_ext/package_reference.py``) so the recorder pattern
    has one implementation. Consumers iterate ``calls`` and never mutate
    it — that read-only contract is what makes :func:`replay_setup`'s
    cache safe.

    Examples
    --------
    >>> recorder = SetupRecorder()
    >>> recorder.add_directive("foo-bar", object)
    >>> recorder.add_role("baz-quux", lambda *a, **k: None)
    >>> [name for name, _, _ in recorder.calls]
    ['add_directive', 'add_role']
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def __getattr__(self, attr: str) -> t.Callable[..., None]:
        def _recorder(*args: object, **kwargs: object) -> None:
            self.calls.append((attr, args, kwargs))

        return _recorder


@functools.cache
def replay_setup(module_name: str) -> SetupRecorder | None:
    """Run a module's ``setup()`` against a recorder; return None on failure.

    Cached because every invocation of ``autodirectives`` / ``autoroles``
    calls in here, and a docs build with N package pages × M directive
    invocations would otherwise re-import + re-replay each package's
    ``setup()`` for every call. The recorder is read-only by contract
    (consumers iterate ``recorder.calls`` and never mutate it). Tests
    that depend on a side effect of replay (e.g. log emission for a
    raising ``setup()``) should call ``replay_setup.cache_clear()``
    before asserting.

    Examples
    --------
    >>> recorder = replay_setup("sphinx_autodoc_docutils")
    >>> recorder is not None
    True
    >>> any(name == "add_directive" for name, _, _ in recorder.calls)
    True
    """
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return None
    setup_fn = getattr(module, "setup", None)
    if not callable(setup_fn):
        return None
    recorder = SetupRecorder()
    try:
        setup_fn(recorder)
    except Exception:  # noqa: BLE001 - extension setup errors are expected here
        logger.debug(
            "setup replay failed for %s; falling back to module introspection",
            module_name,
            exc_info=True,
        )
        return None
    return recorder


def _registered_directives(module_name: str) -> list[tuple[str, type[Directive]]]:
    """Return ``(registered_name, cls)`` pairs from a package's ``setup()``.

    Falls back to module introspection when the module has no ``setup()``,
    so passing a directive-defining submodule (``pkg._directives``) keeps
    working.

    Examples
    --------
    >>> pairs = _registered_directives("sphinx_autodoc_docutils")
    >>> ("autodirectives", AutoDirectives) in pairs
    True
    """
    recorder = replay_setup(module_name)
    if recorder is not None:
        pairs: list[tuple[str, type[Directive]]] = []
        for call_name, args, _kwargs in recorder.calls:
            if call_name == "add_directive" and len(args) >= 2:
                name, cls = args[0], args[1]
                if (
                    isinstance(name, str)
                    and inspect.isclass(cls)
                    and issubclass(cls, Directive)
                ):
                    pairs.append((name, cls))
            elif call_name == "add_directive_to_domain" and len(args) >= 3:
                name, cls = args[1], args[2]
                if (
                    isinstance(name, str)
                    and inspect.isclass(cls)
                    and issubclass(cls, Directive)
                ):
                    pairs.append((name, cls))
        if pairs:
            return pairs
    return [
        (_registered_name(name), cls) for name, cls in _directive_classes(module_name)
    ]


def _registered_roles(module_name: str) -> list[tuple[str, object]]:
    """Return ``(registered_name, role_fn)`` pairs from a package's ``setup()``.

    Falls back to module introspection when no ``setup()`` is found, or when
    the package's ``setup()`` registers nothing via ``app.add_role`` (e.g.,
    ``sphinx_autodoc_argparse`` exposes role registration through
    ``register_roles(app)`` rather than wiring it into ``setup()`` itself).

    Examples
    --------
    >>> pairs = _registered_roles("sphinx_autodoc_fastmcp")
    >>> any(name == "tool" for name, _ in pairs)
    True
    >>> pairs = _registered_roles("sphinx_autodoc_argparse.roles")
    >>> any(name == "cli-option" for name, _ in pairs)
    True
    """
    recorder = replay_setup(module_name)
    if recorder is not None:
        pairs: list[tuple[str, object]] = []
        for call_name, args, _kwargs in recorder.calls:
            if call_name == "add_role" and len(args) >= 2:
                name, role_fn = args[0], args[1]
                if isinstance(name, str) and callable(role_fn):
                    pairs.append((name, role_fn))
            elif call_name == "add_role_to_domain" and len(args) >= 3:
                name, role_fn = args[1], args[2]
                if isinstance(name, str) and callable(role_fn):
                    pairs.append((name, role_fn))
        if pairs:
            return pairs
    return [(_registered_name(name), fn) for name, fn in _role_callables(module_name)]


def _directive_classes(module_name: str) -> list[tuple[str, type[Directive]]]:
    """Return public docutils directive classes in a module.

    Examples
    --------
    >>> directives = _directive_classes("sphinx_autodoc_docutils._directives")
    >>> any(name == "AutoDirectives" for name, _value in directives)
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
    >>> roles = _role_callables("sphinx_autodoc_argparse.roles")
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
    >>> _registered_name("AutoDirectives")
    'autodirectives'
    >>> _registered_name("cli_option_role")
    'cli-option'
    """
    explicit = {
        "AutoDirective": "autodirective",
        "AutoDirectives": "autodirectives",
        "AutoRole": "autorole",
        "AutoRoles": "autoroles",
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


def _literal_paragraph(text: str) -> nodes.paragraph:
    """Return a paragraph containing one literal node."""
    paragraph = nodes.paragraph()
    paragraph += nodes.literal(text, text)
    return paragraph


def _option_field_list(option_spec: OptionSpec | None) -> nodes.field_list | None:
    """Return a field-list representation of an option spec."""
    rows = _option_rows(option_spec)
    if not rows:
        return None
    field_list = nodes.field_list()
    for row in rows:
        option_name, converter_name = row.split("|")[1:3]
        clean_option_name = option_name.strip().strip("`")
        clean_converter_name = converter_name.strip().strip("`")
        field_list += nodes.field(
            "",
            nodes.field_name("", clean_option_name),
            nodes.field_body("", _literal_paragraph(clean_converter_name)),
        )
    return field_list


def _entry_kind(desc_node: addnodes.desc) -> str:
    """Return the badge label for one parsed ``rst`` description node."""
    objtype = str(desc_node.get("objtype", ""))
    if objtype == "directive:option":
        return "option"
    return objtype


def _inject_docutils_badges(node_list: list[nodes.Node]) -> None:
    """Attach shared badge-slot metadata to parsed ``rst:*`` entries."""
    for desc_node in iter_desc_nodes(node_list):
        if desc_node.get("domain") != "rst":
            continue
        badge_group = build_kind_badge_group(_entry_kind(desc_node))
        for sig_node in desc_node.children:
            if not isinstance(sig_node, addnodes.desc_signature):
                continue
            inject_signature_slots(
                sig_node,
                marker_attr="sadoc_badges_injected",
                badge_node=badge_group.deepcopy(),
                extract_source_link=False,
            )


def _render_markup_nodes(
    directive: SphinxDirective,
    markup: str,
) -> list[nodes.Node]:
    """Parse markup and attach layout metadata for docutils entries."""
    node_list = parse_generated_markup(directive, markup)
    _inject_docutils_badges(node_list)
    return node_list


def _content_node(desc_node: addnodes.desc) -> addnodes.desc_content | None:
    """Return the first ``desc_content`` child for ``desc_node``."""
    return next(
        (
            child
            for child in desc_node.children
            if isinstance(child, addnodes.desc_content)
        ),
        None,
    )


def _insert_after_summary(
    content: addnodes.desc_content,
    node: nodes.Node,
) -> None:
    """Insert *node* after the leading summary paragraphs in ``content``."""
    insert_idx = 0
    while insert_idx < len(content.children) and isinstance(
        content.children[insert_idx],
        nodes.paragraph,
    ):
        insert_idx += 1
    content.insert(insert_idx, node)


def _directive_fact_rows(
    path: str,
    directive_cls: type[Directive],
) -> list[ApiFactRow]:
    """Return shared fact rows for one autodocumented directive."""
    return [
        ApiFactRow(
            "Python path",
            build_chip_paragraph([build_linked_literal(path)]),
        ),
        ApiFactRow(
            "Required arguments",
            _literal_paragraph(str(directive_cls.required_arguments)),
        ),
        ApiFactRow(
            "Optional arguments",
            _literal_paragraph(str(directive_cls.optional_arguments)),
        ),
        ApiFactRow(
            "Final argument whitespace",
            _literal_paragraph(str(directive_cls.final_argument_whitespace)),
        ),
        ApiFactRow("Has content", _literal_paragraph(str(directive_cls.has_content))),
    ]


def _role_fact_rows(path: str, role_fn: object) -> list[ApiFactRow]:
    """Return shared fact rows for one autodocumented role."""
    rows = [
        ApiFactRow(
            "Python path",
            build_chip_paragraph([build_linked_literal(path)]),
        ),
    ]
    content_value = getattr(role_fn, "content", None)
    if content_value is not None:
        rows.append(
            ApiFactRow("Accepts role content", _literal_paragraph(str(content_value)))
        )
    return rows


def _normalize_directive_nodes(
    node_list: list[nodes.Node],
    *,
    path: str,
    directive_cls: type[Directive],
) -> None:
    """Attach shared facts/options sections to parsed directive entries."""
    for desc_node in iter_desc_nodes(node_list):
        if desc_node.get("domain") != "rst" or desc_node.get("objtype") != "directive":
            continue
        content = _content_node(desc_node)
        if content is None:
            continue
        option_descs = [
            child
            for child in list(content.children)
            if isinstance(child, addnodes.desc)
            and child.get("domain") == "rst"
            and child.get("objtype") == "directive:option"
        ]
        for option_desc in option_descs:
            content.remove(option_desc)
        _insert_after_summary(
            content,
            build_api_facts_section(_directive_fact_rows(path, directive_cls)),
        )
        if option_descs:
            content += build_api_table_section(API.OPTIONS, *option_descs)


def _normalize_role_nodes(
    node_list: list[nodes.Node],
    *,
    path: str,
    role_fn: object,
) -> None:
    """Attach shared facts/options sections to parsed role entries."""
    option_field_list = _option_field_list(getattr(role_fn, "options", None))
    for desc_node in iter_desc_nodes(node_list):
        if desc_node.get("domain") != "rst" or desc_node.get("objtype") != "role":
            continue
        content = _content_node(desc_node)
        if content is None:
            continue
        _insert_after_summary(
            content,
            build_api_facts_section(_role_fact_rows(path, role_fn)),
        )
        if option_field_list is not None:
            content += build_api_table_section(
                API.OPTIONS,
                option_field_list.deepcopy(),
            )


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
    ]
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
        rendered = _render_markup_nodes(
            self,
            _directive_markup(
                path,
                directive_cls,
                directive_name=_registered_name(attr_name),
                no_index="no-index" in self.options,
            ),
        )
        _normalize_directive_nodes(rendered, path=path, directive_cls=directive_cls)
        return rendered


class AutoDirectives(SphinxDirective):
    """Render documentation for every directive a package registers.

    Accepts either an extension package (whose ``setup()`` runs against a
    recorder so each ``app.add_directive(name, cls)`` call surfaces by its
    real registered name) or a directive-defining module (introspected for
    ``Directive`` subclasses, with names derived from class names).
    """

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        module_name = self.arguments[0]
        no_index = "no-index" in self.options
        results: list[nodes.Node] = []
        for registered_name, directive_cls in _registered_directives(module_name):
            path = f"{directive_cls.__module__}.{directive_cls.__name__}"
            rendered = _render_markup_nodes(
                self,
                _directive_markup(
                    path,
                    directive_cls,
                    directive_name=registered_name,
                    no_index=no_index,
                ),
            )
            _normalize_directive_nodes(rendered, path=path, directive_cls=directive_cls)
            results.extend(rendered)
        return results


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
        rendered = _render_markup_nodes(
            self,
            _role_markup(
                path,
                role_name,
                role_fn,
                no_index="no-index" in self.options,
            ),
        )
        _normalize_role_nodes(rendered, path=path, role_fn=role_fn)
        return rendered


class AutoRoles(SphinxDirective):
    """Render documentation for every role a package registers.

    Accepts either an extension package (whose ``setup()`` runs against a
    recorder so each ``app.add_role(name, fn)`` call surfaces by its real
    registered name) or a role-defining module (introspected for ``*_role``
    callables, with names derived from function names).
    """

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        module_name = self.arguments[0]
        no_index = "no-index" in self.options
        results: list[nodes.Node] = []
        for registered_name, role_fn in _registered_roles(module_name):
            role_module = getattr(role_fn, "__module__", module_name)
            role_attr = getattr(role_fn, "__name__", registered_name)
            path = f"{role_module}.{role_attr}"
            rendered = _render_markup_nodes(
                self,
                _role_markup(
                    path,
                    registered_name,
                    role_fn,
                    no_index=no_index,
                ),
            )
            _normalize_role_nodes(rendered, path=path, role_fn=role_fn)
            results.extend(rendered)
        return results
