"""Rendering directives for Sphinx configuration value documentation.

Examples
--------
>>> values = discover_config_values("sphinx_fonts")
>>> {value.name for value in values} == {
...     "sphinx_fonts",
...     "sphinx_font_fallbacks",
...     "sphinx_font_css_variables",
...     "sphinx_font_preload",
... }
True

>>> markup = render_config_index_markup("sphinx_fonts")
>>> ".. list-table::" in markup
True
"""

from __future__ import annotations

import importlib
import pprint
import typing as t
from dataclasses import dataclass

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx import addnodes
from sphinx.util.docutils import SphinxDirective

if t.TYPE_CHECKING:
    from sphinx.util.typing import OptionSpec

_COMPLEX_REPR_THRESHOLD = 60


class InvalidConfigValuePathError(ValueError):
    """Raised when a config-value path is missing the ``module.option`` form.

    Examples
    --------
    >>> str(InvalidConfigValuePathError("demo"))
    "Expected 'module_name.config_value', got 'demo'"
    """

    def __init__(self, path: str) -> None:
        super().__init__(f"Expected 'module_name.config_value', got {path!r}")


class UnknownConfigValueError(LookupError):
    """Raised when a module does not register a requested config value.

    Examples
    --------
    >>> str(UnknownConfigValueError("demo_ext", "missing"))
    "No config value named 'missing' registered by 'demo_ext'"
    """

    def __init__(self, module_name: str, value_name: str) -> None:
        super().__init__(
            f"No config value named {value_name!r} registered by {module_name!r}"
        )


@dataclass(frozen=True)
class SphinxConfigValue:
    """Recorded metadata for a config value registered via ``setup()``.

    Examples
    --------
    >>> value = SphinxConfigValue(
    ...     module_name="demo_ext",
    ...     name="demo_option",
    ...     default=True,
    ...     rebuild="html",
    ...     types=(bool,),
    ... )
    >>> value.qualified_name
    'demo_ext.demo_option'
    """

    module_name: str
    name: str
    default: object  # object: config defaults are genuinely heterogeneous
    rebuild: str
    types: object = ()  # object: Sphinx allows ENUM, not just type
    description: str = ""

    @property
    def qualified_name(self) -> str:
        """Return the fully-qualified value path used by the single directive.

        Examples
        --------
        >>> value = SphinxConfigValue("demo_ext", "demo_option", None, "")
        >>> value.qualified_name
        'demo_ext.demo_option'
        """
        return f"{self.module_name}.{self.name}"


class RecorderApp:
    """Minimal Sphinx-app recorder used to observe ``setup()`` calls.

    Examples
    --------
    >>> app = RecorderApp()
    >>> app.add_config_value("demo_option", True, "html")
    >>> app.calls[0][0]
    'add_config_value'
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def __getattr__(self, name: str) -> t.Callable[..., None]:
        """Record arbitrary method calls without implementing Sphinx itself.

        Examples
        --------
        >>> app = RecorderApp()
        >>> app.setup_extension("demo_ext")
        >>> app.calls[0][0]
        'setup_extension'
        """

        def _record(
            *args: object, **kwargs: object
        ) -> None:  # object: universal __getattr__ stub
            self.calls.append((name, args, kwargs))

        return _record


def _call_setup(module_name: str) -> RecorderApp:
    """Run a module's ``setup()`` function against a recorder app.

    Examples
    --------
    >>> app = _call_setup("sphinx_fonts")
    >>> any(name == "add_config_value" for name, _args, _kwargs in app.calls)
    True
    """
    module = importlib.import_module(module_name)
    app = RecorderApp()
    setup = module.setup
    setup(app)
    return app


def _render_default(value: object) -> str:  # object: only calls repr()
    """Render a compact literal for a ``:default:`` option.

    Examples
    --------
    >>> _render_default(True)
    '``True``'
    >>> _render_default("demo")
    "``'demo'``"
    """
    return f"``{value!r}``"


def _is_complex_default(value: object) -> bool:  # object: only calls repr()
    """Return True when repr of value exceeds the inline display threshold.

    Values whose repr is longer than :data:`_COMPLEX_REPR_THRESHOLD` chars
    are rendered as a Pygments-highlighted ``literal_block`` node rather than
    as an inline ``:default:`` field literal.

    Examples
    --------
    >>> _is_complex_default(True)
    False
    >>> _is_complex_default("warning")
    False
    >>> _is_complex_default(frozenset(range(15)))
    True
    """
    return len(repr(value)) > _COMPLEX_REPR_THRESHOLD


def _make_default_block(value: object) -> nodes.literal_block:  # object: calls repr
    """Return a Pygments-highlighted ``literal_block`` for a complex default.

    The ``language='python'`` attribute causes Sphinx's HTML writer to call
    ``highlighter.highlight_block()``, producing ``<div class="highlight-python">``.

    Examples
    --------
    >>> block = _make_default_block({"k": "v"})
    >>> block["language"]
    'python'
    >>> "'k'" in block.astext()
    True
    """
    formatted = pprint.pformat(value, width=72)
    block = nodes.literal_block(formatted, formatted)
    block["language"] = "python"
    block["linenos"] = False
    block["highlight_args"] = {}
    block["force"] = False
    return block


def _render_types(
    types: object, default: object
) -> str:  # object: uses isinstance guards
    """Render a readable type expression for ``:type:``.

    Examples
    --------
    >>> _render_types((bool, str), False)
    '``bool | str``'
    >>> _render_types((), None)
    '``None``'
    """
    if isinstance(types, (list, tuple, set, frozenset)) and types:
        names = sorted(
            "None" if getattr(item, "__name__", "") == "NoneType" else item.__name__
            for item in t.cast(t.Iterable[type], types)
        )
        return f"``{' | '.join(names)}``"
    if types:
        return f"``{types!r}``"
    if default is None:
        return "``None``"
    return f"``{type(default).__name__}``"


def _config_values_from_calls(
    module_name: str,
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]],
) -> list[SphinxConfigValue]:
    """Extract config-value metadata from recorded setup calls.

    Handles both positional and keyword-style ``add_config_value()`` calls.

    Examples
    --------
    Positional args:

    >>> values = _config_values_from_calls(
    ...     "demo_ext",
    ...     [("add_config_value", ("demo_option", 1, "env"), {"types": (int,)})],
    ... )
    >>> values[0].name
    'demo_option'

    Keyword args (name positional, rest as kwargs):

    >>> kw_args = {"default": True, "rebuild": "html"}
    >>> kw_call = ("add_config_value", ("kw_opt",), kw_args)
    >>> values = _config_values_from_calls("demo_ext", [kw_call])
    >>> values[0].name
    'kw_opt'
    >>> values[0].default
    True
    >>> values[0].rebuild
    'html'
    """
    values: list[SphinxConfigValue] = []
    seen: set[str] = set()
    for call_name, args, kwargs in calls:
        if call_name != "add_config_value" or len(args) < 1:
            continue
        name = str(args[0])
        if name in seen:
            continue
        seen.add(name)
        values.append(
            SphinxConfigValue(
                module_name=module_name,
                name=name,
                default=kwargs.get("default", args[1] if len(args) > 1 else None),
                rebuild=str(kwargs.get("rebuild", args[2] if len(args) > 2 else "")),
                types=kwargs.get("types", args[3] if len(args) > 3 else ()),
                description=str(
                    kwargs.get("description", args[4] if len(args) > 4 else "")
                ),
            )
        )
    return values


def discover_config_values(module_name: str) -> list[SphinxConfigValue]:
    """Return config values registered by a Sphinx extension module.

    Examples
    --------
    >>> names = {value.name for value in discover_config_values("sphinx_argparse_neo")}
    >>> names == {
    ...     "argparse_group_title_prefix",
    ...     "argparse_show_defaults",
    ...     "argparse_show_choices",
    ...     "argparse_show_types",
    ... }
    True
    """
    app = _call_setup(module_name)
    return _config_values_from_calls(module_name, app.calls)


def discover_config_value(path: str) -> SphinxConfigValue:
    """Return one config value from a fully-qualified path.

    Examples
    --------
    >>> value = discover_config_value("sphinx_fonts.sphinx_font_preload")
    >>> value.name
    'sphinx_font_preload'
    """
    module_name, _, value_name = path.rpartition(".")
    if not module_name or not value_name:
        raise InvalidConfigValuePathError(path)
    for value in discover_config_values(module_name):
        if value.name == value_name:
            return value
    raise UnknownConfigValueError(module_name, value_name)


def render_config_value_markup(
    value: SphinxConfigValue, *, no_index: bool = False
) -> str:
    """Return reStructuredText for one real ``confval`` entry.

    Simple defaults (repr ≤ :data:`_COMPLEX_REPR_THRESHOLD` chars) use the
    inline ``:default:`` field.  Complex defaults omit the field; callers that
    need Pygments output should inject a :func:`_make_default_block` node into
    the parsed ``desc_content`` directly.

    Examples
    --------
    >>> value = SphinxConfigValue("demo_ext", "demo_option", True, "html", (bool,))
    >>> markup = render_config_value_markup(value)
    >>> ".. confval:: demo_option" in markup
    True
    >>> ":default: ``True``" in markup
    True
    """
    lines = [
        f".. confval:: {value.name}",
        "   :no-index:" if no_index else "",
        f"   :type: {_render_types(value.types, value.default)}",
    ]
    if not _is_complex_default(value.default):
        lines.append(f"   :default: {_render_default(value.default)}")
    lines.append("")
    if value.description:
        lines.extend([f"   {value.description}", ""])
    lines.extend(
        [
            f"   Registered by ``{value.module_name}.setup()``.",
            "",
            f"   Rebuild: ``{value.rebuild or 'none'}``.",
        ]
    )
    return "\n".join(lines)


def render_config_values_markup(module_name: str, *, no_index: bool = False) -> str:
    """Return reStructuredText for every config value from a module.

    Examples
    --------
    >>> markup = render_config_values_markup("sphinx_fonts")
    >>> ".. confval:: sphinx_fonts" in markup
    True
    """
    return "\n\n".join(
        render_config_value_markup(value, no_index=no_index)
        for value in discover_config_values(module_name)
    )


def render_config_index_markup(
    module_name: str, *, heading: str = "Config Value Index"
) -> str:
    """Return a list-table index summarizing a module's config values.

    Examples
    --------
    >>> markup = render_config_index_markup("sphinx_fonts")
    >>> "sphinx_font_preload" in markup
    True
    """
    values = discover_config_values(module_name)
    if not values:
        return ""

    lines = [
        f".. rubric:: {heading}",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        "",
        "   * - Name",
        "     - Type",
        "     - Default",
        "     - Rebuild",
    ]
    for value in values:
        lines.extend(
            [
                f"   * - ``{value.name}``",
                f"     - {_render_types(value.types, value.default)}",
                f"     - {_render_default(value.default)}",
                f"     - ``{value.rebuild or 'none'}``",
            ]
        )
    return "\n".join(lines)


# NOTE: This function is byte-for-byte identical to
# sphinx_autodoc_docutils._directives._render_blocks.  Both packages depend
# only on sphinx (not on each other), so a shared location would require a new
# dependency.  If a third caller emerges, extract to gp_sphinx._render.
def _render_blocks(directive: SphinxDirective, markup: str) -> list[nodes.Node]:
    """Parse generated markup back through Sphinx.

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


def _iter_desc_content(
    node_list: list[nodes.Node],
) -> t.Iterator[addnodes.desc_content]:
    """Yield ``desc_content`` nodes from a list of parsed nodes.

    ``addnodes.desc_content`` is the ``<dd>`` body of a Sphinx object
    description (confval, function, etc.).

    Examples
    --------
    >>> list(_iter_desc_content([]))
    []
    """
    for node in node_list:
        yield from node.traverse(addnodes.desc_content)


class AutoconfigvalueDirective(SphinxDirective):
    """Render one config value from a fully-qualified ``module.option`` path."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        value = discover_config_value(self.arguments[0])
        return _render_blocks(
            self,
            render_config_value_markup(value, no_index="no-index" in self.options),
        )


class AutoconfigvaluesDirective(SphinxDirective):
    """Render all config values registered by one extension module."""

    required_arguments = 1
    has_content = False
    option_spec: t.ClassVar[OptionSpec] = {"no-index": directives.flag}

    def run(self) -> list[nodes.Node]:
        module_name = self.arguments[0]
        no_index = "no-index" in self.options
        result: list[nodes.Node] = []
        for value in discover_config_values(module_name):
            markup = render_config_value_markup(value, no_index=no_index)
            value_nodes = _render_blocks(self, markup)
            if _is_complex_default(value.default):
                block = _make_default_block(value.default)
                for desc_content in _iter_desc_content(value_nodes):
                    # Insert before the trailing metadata paragraphs
                    # ("Registered by …" and "Rebuild: …")
                    idx = max(0, len(desc_content) - 2)
                    desc_content.insert(idx, block)
            result.extend(value_nodes)
        return result


class AutoconfigvalueIndexDirective(SphinxDirective):
    """Render a summary table for a module's config values."""

    required_arguments = 1
    has_content = False

    def run(self) -> list[nodes.Node]:
        markup = render_config_index_markup(self.arguments[0])
        return _render_blocks(self, markup) if markup else []


class AutosphinxconfigIndexDirective(SphinxDirective):
    """Render a drop-in index plus detailed ``confval`` blocks.

    This keeps the legacy directive useful on package pages without forcing
    authors to remember a second directive just to get the detailed entries.
    """

    required_arguments = 1
    has_content = False

    def run(self) -> list[nodes.Node]:
        module_name = self.arguments[0]
        parts = [
            render_config_index_markup(module_name, heading="Sphinx Config Index"),
            render_config_values_markup(module_name),
        ]
        markup = "\n\n".join(part for part in parts if part)
        return _render_blocks(self, markup) if markup else []
