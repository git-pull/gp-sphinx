"""Collect FastMCP tool / prompt / resource metadata at Sphinx build time."""

from __future__ import annotations

import contextlib
import importlib
import inspect
import logging
import re
import typing as t

from sphinx.application import Sphinx

from sphinx_autodoc_fastmcp._models import (
    DEFAULT_AXES,
    Axis,
    PromptArgInfo,
    PromptInfo,
    ResourceInfo,
    ResourceTemplateInfo,
    ToolInfo,
    coerce_axes,
    resolve_axes,
)
from sphinx_autodoc_fastmcp._parsing import extract_params, first_paragraph
from sphinx_autodoc_typehints_gp import normalize_annotation_text

logger = logging.getLogger(__name__)


class ToolCollector:
    """Mock FastMCP server that captures tool registrations."""

    def __init__(
        self,
        *,
        area_map: dict[str, str],
        axes: tuple[Axis, ...] = DEFAULT_AXES,
    ) -> None:
        self.tools: list[ToolInfo] = []
        self._current_module: str = ""
        self._area_map = area_map
        self.axes = axes

    def tool(
        self,
        title: str = "",
        annotations: dict[str, bool] | None = None,
        tags: set[str] | None = None,
        meta: dict[str, t.Any] | None = None,
    ) -> t.Callable[[t.Callable[..., t.Any]], t.Callable[..., t.Any]]:
        """Match ``FastMCP.tool()`` decorator behavior for capture."""
        annotations = annotations or {}
        tags = tags or set()
        meta = meta or {}

        def decorator(func: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
            axes = resolve_axes(
                self.axes, tags=tags, annotations=annotations, meta=meta
            )

            module_name = self._current_module
            area = self._area_map.get(
                module_name,
                module_name.replace("_tools", ""),
            )

            self.tools.append(
                ToolInfo(
                    name=func.__name__,
                    title=title or func.__name__.replace("_", " ").title(),
                    module_name=module_name,
                    area=area,
                    axes=axes,
                    annotations=annotations,
                    meta=meta,
                    func=func,
                    docstring=func.__doc__ or "",
                    params=extract_params(func),
                    return_annotation=normalize_annotation_text(
                        inspect.signature(func).return_annotation,
                    ),
                ),
            )
            return func

        return decorator


#: Each hint's documented name paired with the attribute holding it. MCP SDK v2
#: renamed the model fields to snake_case, keeping the camelCase spellings as
#: serialization aliases only — an attribute read has to use the field name.
#: The documented name stays camelCase because that is what the MCP schema
#: publishes and what the rendered pages and ``term_from_annotations`` speak.
_HINTS = (
    ("readOnlyHint", "read_only_hint"),
    ("destructiveHint", "destructive_hint"),
    ("idempotentHint", "idempotent_hint"),
    ("openWorldHint", "open_world_hint"),
)


def _annotation_hints(annotations: t.Any) -> dict[str, bool]:
    """Return the hints a tool actually sets, dropping the unset ones.

    FastMCP accepts ``ToolAnnotations`` or a plain mapping, so read both.
    A mapping is keyed by the documented name; a model by its field.

    Examples
    --------
    >>> _annotation_hints({"readOnlyHint": True, "openWorldHint": None})
    {'readOnlyHint': True}
    >>> _annotation_hints(None)
    {}
    """
    if annotations is None:
        return {}
    hints: dict[str, bool] = {}
    for name, field in _HINTS:
        value = (
            annotations.get(name)
            if isinstance(annotations, dict)
            else getattr(annotations, field, None)
        )
        if isinstance(value, bool):
            hints[name] = value
    return hints


#: Resource and template annotations, documented name paired with the field
#: holding it. Only ``lastModified`` was renamed; the other two already match.
_RESOURCE_ANNOTATION_FIELDS = (
    ("audience", "audience"),
    ("priority", "priority"),
    ("lastModified", "last_modified"),
)


def _tool_from_callable(
    func: t.Callable[..., t.Any],
    *,
    module_name: str,
    area_map: dict[str, str],
    axes: tuple[Axis, ...] = DEFAULT_AXES,
) -> ToolInfo | None:
    """Build ``ToolInfo`` from a decorated function (``__fastmcp__``)."""
    spec = getattr(func, "__fastmcp__", None)
    if spec is None:
        return None
    tags = getattr(spec, "tags", None) or set()
    if not isinstance(tags, set):
        tags = set(tags) if tags else set()
    meta = dict(getattr(spec, "meta", None) or {})
    area = area_map.get(module_name, module_name.replace("_tools", ""))
    name = getattr(spec, "name", None) or func.__name__
    title = getattr(spec, "title", None) or name.replace("_", " ").title()
    ann_dict = _annotation_hints(getattr(spec, "annotations", None))
    resolved = resolve_axes(axes, tags=tags, annotations=ann_dict, meta=meta)
    return ToolInfo(
        name=name,
        title=title,
        module_name=module_name,
        area=area,
        axes=resolved,
        annotations=ann_dict,
        meta=meta,
        func=func,
        docstring=func.__doc__ or "",
        params=extract_params(func),
        return_annotation=normalize_annotation_text(
            inspect.signature(func).return_annotation,
        ),
    )


def _index_by_unique_name(
    index: dict[str, t.Any], name: str, info: t.Any, kind: str
) -> None:
    """Store ``name -> info``, warning when a name is already taken.

    FastMCP keys tools and prompts by name, so a duplicate is a real
    registration the server serves and the docs would otherwise drop in
    silence. First-wins, matching :func:`_index_by_name`'s behaviour for
    URI-keyed components, with a warning naming the collision.
    """
    if name in index:
        logger.warning(
            "sphinx_autodoc_fastmcp: duplicate %s name %r; keeping the first "
            "and skipping the rest",
            kind,
            name,
        )
        return
    index[name] = info


def _tool_from_component(
    tool: t.Any,
    *,
    area_map: dict[str, str],
    axes: tuple[Axis, ...] = DEFAULT_AXES,
) -> ToolInfo:
    """Build ``ToolInfo`` from a live FastMCP ``Tool`` component.

    Sibling of :func:`_tool_from_callable`, which reads the ``__fastmcp__``
    spec a decorator leaves on a function. This reads the registered
    component instead, so it sees what the server actually serves —
    including metadata a hand-written collector cannot carry.

    Module attribution comes from the underlying function rather than the
    position of the module in ``fastmcp_tool_modules``, which is why this
    path does not need that list at all.
    """
    func: t.Callable[..., t.Any] = tool.fn
    if hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    module_name = str(getattr(func, "__module__", "") or "").rpartition(".")[2]

    tags = set(getattr(tool, "tags", None) or ())
    meta = dict(getattr(tool, "meta", None) or {})
    ann_dict = _annotation_hints(getattr(tool, "annotations", None))
    name = str(tool.name)
    area = area_map.get(module_name, module_name.replace("_tools", ""))

    return ToolInfo(
        name=name,
        title=str(getattr(tool, "title", None) or name.replace("_", " ").title()),
        module_name=module_name,
        area=area,
        axes=resolve_axes(axes, tags=tags, annotations=ann_dict, meta=meta),
        annotations=ann_dict,
        meta=meta,
        func=func,
        docstring=func.__doc__ or "",
        params=extract_params(func),
        return_annotation=normalize_annotation_text(
            inspect.signature(func).return_annotation
        ),
    )


def _tools_from_server(
    server: t.Any,
    *,
    area_map: dict[str, str],
    axes: tuple[Axis, ...],
) -> list[ToolInfo] | None:
    """Collect every registered tool off a live server, or ``None``.

    Returns ``None`` when fastmcp is not importable, so the caller can fall
    back to the module-scanning modes rather than reporting zero tools.
    """
    try:
        from fastmcp.tools import Tool as _Tool
    except ImportError:  # pragma: no cover - defensive
        logger.warning(
            "sphinx_autodoc_fastmcp: could not import fastmcp Tool", exc_info=True
        )
        return None
    return [
        _tool_from_component(component, area_map=area_map, axes=axes)
        for component in _iter_components(server)
        if isinstance(component, _Tool) and getattr(component, "fn", None) is not None
    ]


def collect_tools(app: Sphinx) -> None:
    """Populate ``app.env.fastmcp_tools`` from configured modules."""
    modules: list[str] = list(app.config.fastmcp_tool_modules)
    area_map: dict[str, str] = dict(app.config.fastmcp_area_map)
    axes = coerce_axes(app.config.fastmcp_axes)
    mode = str(app.config.fastmcp_collector_mode)
    if mode not in ("register", "introspect"):
        logger.warning(
            "sphinx_autodoc_fastmcp: unknown fastmcp_collector_mode %r; using 'register'",
            mode,
        )
        mode = "register"

    # Prefer the live server when one is configured. The module-scanning modes
    # below cannot see a tool the mock collector rejected, and a rejected kwarg
    # aborts the rest of its module -- so a tool this path reports is a tool the
    # server actually serves. Reads the same provider dict prompts and resources
    # already use, which deliberately bypasses middleware: a toolset gate that
    # hides tools at runtime must not erase them from the documentation.
    server_dotted = str(getattr(app.config, "fastmcp_server_module", "") or "")
    if server_dotted:
        server = _resolve_server_instance(server_dotted)
        if server is not None:
            from_server = _tools_from_server(server, area_map=area_map, axes=axes)
            if from_server:
                tools_by_name: dict[str, ToolInfo] = {}
                for served in from_server:
                    _index_by_unique_name(tools_by_name, served.name, served, "tool")
                app.env.fastmcp_tools = tools_by_name  # type: ignore[attr-defined]
                return

    if not modules:
        logger.warning(
            "sphinx_autodoc_fastmcp: fastmcp_tool_modules is empty; no tools collected",
        )
        app.env.fastmcp_tools = {}  # type: ignore[attr-defined]
        return

    collector_tools: list[ToolInfo] = []

    if mode == "register":
        collector = ToolCollector(area_map=area_map, axes=axes)
        for dotted in modules:
            mod_suffix = dotted.split(".")[-1]
            collector._current_module = mod_suffix
            try:
                mod = importlib.import_module(dotted)
                if hasattr(mod, "register"):
                    mod.register(collector)
            except Exception:
                logger.warning(
                    "sphinx_autodoc_fastmcp: failed to load tool module %s",
                    dotted,
                    exc_info=True,
                )
        collector_tools = collector.tools
    else:
        for dotted in modules:
            mod_suffix = dotted.split(".")[-1]
            try:
                mod = importlib.import_module(dotted)
            except Exception:
                logger.warning(
                    "sphinx_autodoc_fastmcp: failed to import %s",
                    dotted,
                    exc_info=True,
                )
                continue
            for _name, obj in inspect.getmembers(mod):
                if not callable(obj):
                    continue
                info = _tool_from_callable(
                    obj,
                    module_name=mod_suffix,
                    area_map=area_map,
                    axes=axes,
                )
                if info is not None:
                    collector_tools.append(info)

    collected: dict[str, ToolInfo] = {}
    for collected_tool in collector_tools:
        _index_by_unique_name(collected, collected_tool.name, collected_tool, "tool")
    app.env.fastmcp_tools = collected  # type: ignore[attr-defined]


def _resolve_server_instance(dotted: str) -> t.Any | None:
    """Import ``module.attr`` and return a populated ``FastMCP`` instance.

    ``fastmcp_server_module`` may point at either:

    * a live ``FastMCP`` instance — used as-is
    * a zero-argument callable that returns one — invoked once
    * a module whose ``mcp`` attribute is a ``FastMCP`` instance that
      has not yet called its registration hook (common when a server
      exposes ``_register_all()`` and invokes it only from ``run_server``)

    In the last case we call ``register_all()`` / ``_register_all()`` on
    the module after resolving the instance, so docs can enumerate the
    same surface area as a running server.
    """
    if not dotted:
        return None
    if ":" in dotted:
        module_path, attr = dotted.split(":", 1)
    else:
        module_path, _, attr = dotted.rpartition(".")
        if not module_path or not attr:
            logger.warning(
                "sphinx_autodoc_fastmcp: fastmcp_server_module %r has no attribute",
                dotted,
            )
            return None
    try:
        mod = importlib.import_module(module_path)
    except (ImportError, ModuleNotFoundError):
        logger.warning(
            "sphinx_autodoc_fastmcp: could not import server module %s",
            module_path,
            exc_info=True,
        )
        return None
    obj = getattr(mod, attr, None)
    if obj is None:
        return None
    if callable(obj) and not hasattr(obj, "local_provider"):
        try:
            obj = obj()
        except Exception:  # pragma: no cover - defensive
            logger.warning(
                "sphinx_autodoc_fastmcp: calling %s() failed",
                dotted,
                exc_info=True,
            )
            return None
    if getattr(obj, "local_provider", None) is None:
        # Catches both: (a) the configured attribute resolved directly to a
        # non-FastMCP object, and (b) a factory callable that returned one.
        # Without this guard ``_iter_components`` silently yields ``()`` and
        # the user sees empty docs with no diagnostic.
        logger.warning(
            "sphinx_autodoc_fastmcp: %s did not resolve to a FastMCP instance "
            "(no local_provider attribute); prompts/resources will be empty",
            dotted,
        )
        return None
    # Always invoke the server's register-all hook when one is exported.
    # Servers that pre-register some components at import time (decorators)
    # while leaving others to an explicit register_all() would otherwise
    # have those deferred components silently missing from the docs.
    #
    # FastMCP's LocalProvider defaults to on_duplicate="error", so calling
    # register_all() on an already-populated provider raises and would leave
    # the server half-populated. Temporarily switch to "ignore" via a
    # context manager so re-invocation is idempotent. If the hook still
    # raises (real bug, not duplicate), fail closed (return None) — visible
    # empty docs beat partially-wrong docs.
    provider = getattr(obj, "local_provider", None)
    if provider is not None:
        # Instance-first lookup — FastMCP's canonical MCPMixin.register_all
        # is an instance method; module-level register_all is the ad-hoc
        # fallback used by simple scripts.
        hook = (
            getattr(obj, "register_all", None)
            or getattr(obj, "_register_all", None)
            or getattr(mod, "register_all", None)
            or getattr(mod, "_register_all", None)
        )
        if callable(hook):
            try:
                with _ignore_duplicate_policy(provider):
                    # MCPMixin.register_all takes the server as a positional
                    # arg; ad-hoc module-level hooks are zero-arg with the
                    # server captured in a closure.
                    try:
                        hook(obj)
                    except TypeError:
                        hook()
            except Exception:
                logger.warning(
                    "sphinx_autodoc_fastmcp: register-all hook for %s raised; "
                    "skipping server",
                    dotted,
                    exc_info=True,
                )
                return None
    return obj


_MISSING_DUPLICATE_POLICY = object()


@contextlib.contextmanager
def _ignore_duplicate_policy(provider: t.Any) -> t.Iterator[None]:
    """Temporarily set ``provider._on_duplicate = "ignore"`` and restore on exit.

    FastMCP's LocalProvider raises ``ValueError`` when re-registering a
    component under the default ``on_duplicate="error"`` policy. The
    autodoc collector needs idempotent re-invocation, but should not
    permanently mutate the user's provider configuration.

    Sphinx invokes ``builder-inited`` synchronously in the main process
    before any read/write fork (``sphinx/application.py`` ``_init_builder``);
    this manager is therefore safe without locking.
    """
    original = getattr(provider, "_on_duplicate", _MISSING_DUPLICATE_POLICY)
    provider._on_duplicate = "ignore"
    try:
        yield
    finally:
        if original is _MISSING_DUPLICATE_POLICY:
            with contextlib.suppress(AttributeError):
                delattr(provider, "_on_duplicate")
        else:
            provider._on_duplicate = original


def _iter_components(server: t.Any) -> t.Iterable[t.Any]:
    """Yield every FastMCPComponent registered on ``server.local_provider``.

    Bypasses the async ``_list_*`` helpers and iterates the underlying
    ``_components`` dict directly — the helpers are trivial type-filter
    comprehensions, so reading ``_components.values()`` is equivalent and
    avoids needing an event loop at Sphinx build time.
    """
    provider = getattr(server, "local_provider", None)
    if provider is None:
        return ()
    components = getattr(provider, "_components", None)
    if components is None:
        return ()
    return tuple(components.values())


#: FastMCP appends its schema hint as a trailing blank-line-separated
#: paragraph. The wording is not stable — FastMCP 3 wrote "Provide as a JSON
#: string matching the following schema:" and FastMCP 4 writes "Provide a value
#: matching the following JSON schema:" — so match the shape both share rather
#: than either sentence, and only ever consider the final paragraph. Both
#: spellings put the schema object immediately after a colon, and requiring it
#: is what separates the generated note from a written sentence that happens to
#: ask the reader for a JSON schema.
_SCHEMA_NOTE_RE = re.compile(
    r"^Provide\b.*\bJSON\b.*\bschema\b[^{]*:\s*\{", re.IGNORECASE | re.DOTALL
)


def _strip_schema_note(text: str) -> str:
    r"""Remove FastMCP's auto-appended JSON-schema hint from a description.

    FastMCP's prompt argument builder appends a schema hint to help LLMs
    pass non-string arguments; it is noise in human-facing docs.

    Examples
    --------
    >>> _strip_schema_note("Summary.")
    'Summary.'
    >>> _strip_schema_note(
    ...     "Summary.\n\nProvide a value matching the following JSON schema:"
    ...     ' {"type":"number"}. Encode non-string values as JSON.'
    ... )
    'Summary.'
    >>> _strip_schema_note("Summary.\n\nProvide as a JSON string matching the following schema: {}")
    'Summary.'
    >>> _strip_schema_note("First.\n\nSecond.")
    'First.\n\nSecond.'
    >>> _strip_schema_note('Provide a value matching the following JSON schema: {}.')
    ''

    A written paragraph that asks for a schema is not the generated note, and
    survives — the note always carries the schema object after its colon.

    >>> _strip_schema_note("The filter.\n\nProvide a JSON schema for the rows.")
    'The filter.\n\nProvide a JSON schema for the rows.'
    """
    head, sep, tail = text.rpartition("\n\n")
    # Without a separator the note is the whole description, and `head` is
    # already the empty string this should return.
    if _SCHEMA_NOTE_RE.match((tail if sep else text).strip()):
        return head.strip()
    return text.strip()


def _prompt_from_component(prompt: t.Any) -> PromptInfo:
    """Build a ``PromptInfo`` from a FastMCP ``Prompt`` component."""
    arguments: list[PromptArgInfo] = []
    for arg in getattr(prompt, "arguments", None) or []:
        arguments.append(
            PromptArgInfo(
                name=str(arg.name),
                description=_strip_schema_note(str(arg.description or "")),
                required=bool(arg.required),
                type_str="",
            ),
        )
    func = getattr(prompt, "fn", None)
    if func is not None and hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    docstring = (func.__doc__ or "") if func is not None else ""
    if func is not None and arguments:
        # Enrich argument metadata with signature type annotations where
        # possible so the rendered table can show types, not just names.
        try:
            sig = inspect.signature(func)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            sig = None
        if sig is not None:
            for arg in arguments:
                param = sig.parameters.get(arg.name)
                if param is not None:
                    arg.type_str = normalize_annotation_text(param.annotation)
    tags = tuple(sorted(str(tag) for tag in getattr(prompt, "tags", None) or ()))
    module_name = getattr(func, "__module__", "") if func is not None else ""
    return PromptInfo(
        name=str(prompt.name),
        title=str(prompt.title or prompt.name),
        description=first_paragraph(str(prompt.description or "")),
        docstring=docstring,
        tags=tags,
        arguments=arguments,
        module_name=module_name,
    )


def _resource_from_component(res: t.Any) -> ResourceInfo:
    """Build a ``ResourceInfo`` from a FastMCP ``Resource`` component."""
    func = getattr(res, "fn", None)
    if func is not None and hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    docstring = (func.__doc__ or "") if func is not None else ""
    tags = tuple(sorted(str(tag) for tag in getattr(res, "tags", None) or ()))
    annotations = getattr(res, "annotations", None)
    ann_dict: dict[str, t.Any] = {}
    if annotations is not None:
        for name, field in _RESOURCE_ANNOTATION_FIELDS:
            val = getattr(annotations, field, None)
            if val is not None:
                ann_dict[name] = val
    module_name = getattr(func, "__module__", "") if func is not None else ""
    return ResourceInfo(
        name=str(res.name),
        uri=str(res.uri),
        title=str(res.title or res.name),
        description=first_paragraph(str(res.description or "")),
        mime_type=str(getattr(res, "mime_type", "") or ""),
        docstring=docstring,
        tags=tags,
        annotations=ann_dict,
        module_name=module_name,
    )


def _template_params_from_schema(
    schema: dict[str, t.Any] | None,
) -> list[PromptArgInfo]:
    """Flatten a JSON Schema ``properties`` dict into ``PromptArgInfo`` rows.

    Examples
    --------
    >>> _template_params_from_schema(None)
    []
    >>> _template_params_from_schema({})
    []
    >>> _template_params_from_schema({"properties": {"n": {"type": "string"}}, "required": ["n"]})
    [PromptArgInfo(name='n', description='', required=True, type_str='string')]
    """
    if not schema:
        return []
    props = schema.get("properties") or {}
    required = set(schema.get("required") or ())
    rows: list[PromptArgInfo] = []
    for name, subschema in props.items():
        if not isinstance(subschema, dict):
            continue
        type_str = str(subschema.get("type", "")) if subschema.get("type") else ""
        # Anyof/oneof unions: join short type names.
        if not type_str:
            union = subschema.get("anyOf") or subschema.get("oneOf") or ()
            parts = [
                str(member.get("type", ""))
                for member in union
                if isinstance(member, dict) and member.get("type")
            ]
            if parts:
                type_str = " | ".join(parts)
        rows.append(
            PromptArgInfo(
                name=str(name),
                description=str(subschema.get("description", "") or ""),
                required=name in required,
                type_str=type_str,
            ),
        )
    return rows


def _resource_template_from_component(tpl: t.Any) -> ResourceTemplateInfo:
    """Build a ``ResourceTemplateInfo`` from a ``ResourceTemplate`` component."""
    func = getattr(tpl, "fn", None)
    if func is not None and hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    docstring = (func.__doc__ or "") if func is not None else ""
    tags = tuple(sorted(str(tag) for tag in getattr(tpl, "tags", None) or ()))
    annotations = getattr(tpl, "annotations", None)
    ann_dict: dict[str, t.Any] = {}
    if annotations is not None:
        for name, field in _RESOURCE_ANNOTATION_FIELDS:
            val = getattr(annotations, field, None)
            if val is not None:
                ann_dict[name] = val
    parameters = _template_params_from_schema(getattr(tpl, "parameters", None))
    module_name = getattr(func, "__module__", "") if func is not None else ""
    return ResourceTemplateInfo(
        name=str(tpl.name),
        uri_template=str(tpl.uri_template),
        title=str(tpl.title or tpl.name),
        description=first_paragraph(str(tpl.description or "")),
        mime_type=str(getattr(tpl, "mime_type", "") or ""),
        parameters=parameters,
        docstring=docstring,
        tags=tags,
        annotations=ann_dict,
        module_name=module_name,
    )


def collect_prompts_and_resources(app: Sphinx) -> None:
    """Populate ``app.env.fastmcp_prompts`` / ``_resources`` / ``_resource_templates``.

    Imports ``fastmcp_server_module`` (e.g. ``"pkg.server:mcp"``) and
    enumerates the live FastMCP instance's registered components.  Does
    nothing if the config value is unset.

    Examples
    --------
    >>> import types
    >>> app = types.SimpleNamespace(
    ...     config=types.SimpleNamespace(fastmcp_server_module=""),
    ...     env=types.SimpleNamespace(),
    ... )
    >>> collect_prompts_and_resources(app)
    >>> app.env.fastmcp_prompts
    {}
    >>> app.env.fastmcp_resources
    {}
    >>> app.env.fastmcp_resource_names
    {}
    >>> app.env.fastmcp_resource_templates
    {}
    >>> app.env.fastmcp_resource_template_names
    {}
    """
    server_dotted = str(getattr(app.config, "fastmcp_server_module", "") or "")
    prompts: dict[str, PromptInfo] = {}
    # Resources and templates are URI-keyed because FastMCP itself keys by
    # ``str(uri)`` / ``uri_template`` (see fastmcp/resources/base.py:Resource.key).
    # Two distinct resources sharing a ``.name`` would silently overwrite each
    # other if we keyed by name. The companion ``*_names`` dicts let
    # ``{fastmcp-resource} my_resource`` directives resolve by friendly name
    # while still preserving URI identity for collisions.
    resources: dict[str, ResourceInfo] = {}
    resource_names: dict[str, str] = {}
    templates: dict[str, ResourceTemplateInfo] = {}
    template_names: dict[str, str] = {}

    if server_dotted:
        server = _resolve_server_instance(server_dotted)
        if server is None:
            logger.warning(
                "sphinx_autodoc_fastmcp: fastmcp_server_module %r did not resolve "
                "to a FastMCP instance; prompts/resources will be empty",
                server_dotted,
            )
        else:
            try:
                # Local imports so callers without fastmcp installed don't pay
                # the import cost unless they actually point at a server.
                from fastmcp.prompts.base import Prompt as _Prompt
                from fastmcp.resources.base import Resource as _Resource
                from fastmcp.resources.template import (
                    ResourceTemplate as _ResourceTemplate,
                )
            except ImportError:  # pragma: no cover - defensive
                logger.warning(
                    "sphinx_autodoc_fastmcp: could not import fastmcp types",
                    exc_info=True,
                )
            else:
                for component in _iter_components(server):
                    if isinstance(component, _ResourceTemplate):
                        info_tpl = _resource_template_from_component(component)
                        key_tpl = str(info_tpl.uri_template)
                        templates[key_tpl] = info_tpl
                        _index_by_name(
                            template_names, info_tpl.name, key_tpl, "template"
                        )
                    elif isinstance(component, _Resource):
                        info_res = _resource_from_component(component)
                        key_res = str(info_res.uri)
                        resources[key_res] = info_res
                        _index_by_name(
                            resource_names, info_res.name, key_res, "resource"
                        )
                    elif isinstance(component, _Prompt):
                        info_p = _prompt_from_component(component)
                        _index_by_unique_name(prompts, info_p.name, info_p, "prompt")

    app.env.fastmcp_prompts = prompts  # type: ignore[attr-defined]
    app.env.fastmcp_resources = resources  # type: ignore[attr-defined]
    app.env.fastmcp_resource_names = resource_names  # type: ignore[attr-defined]
    app.env.fastmcp_resource_templates = templates  # type: ignore[attr-defined]
    app.env.fastmcp_resource_template_names = template_names  # type: ignore[attr-defined]


def _index_by_name(name_index: dict[str, str], name: str, key: str, kind: str) -> None:
    """Record ``name -> key`` mapping; warn on first-wins collision.

    FastMCP allows two distinct resources/templates to share a display name
    while remaining keyed apart by URI. Authoring docs by name is convenient
    but ambiguous in that case — first-wins, with a clear warning so users
    know to disambiguate by URI.
    """
    existing = name_index.get(name)
    if existing is not None and existing != key:
        logger.warning(
            "sphinx_autodoc_fastmcp: %s name %r is ambiguous "
            "(%s and %s share it); resolving to %s",
            kind,
            name,
            existing,
            key,
            existing,
        )
        return
    name_index[name] = key
