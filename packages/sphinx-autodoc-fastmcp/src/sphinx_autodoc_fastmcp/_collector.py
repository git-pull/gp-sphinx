"""Collect FastMCP tool / prompt / resource metadata at Sphinx build time."""

from __future__ import annotations

import importlib
import inspect
import logging
import typing as t

from sphinx.application import Sphinx

from sphinx_autodoc_fastmcp._models import (
    PromptArgInfo,
    PromptInfo,
    ResourceInfo,
    ResourceTemplateInfo,
    ToolInfo,
)
from sphinx_autodoc_fastmcp._parsing import extract_params, first_paragraph
from sphinx_autodoc_typehints_gp import normalize_annotation_text

logger = logging.getLogger(__name__)

TAG_READONLY = "readonly"
TAG_MUTATING = "mutating"
TAG_DESTRUCTIVE = "destructive"


class ToolCollector:
    """Mock FastMCP server that captures tool registrations."""

    def __init__(
        self,
        *,
        area_map: dict[str, str],
    ) -> None:
        self.tools: list[ToolInfo] = []
        self._current_module: str = ""
        self._area_map = area_map

    def tool(
        self,
        title: str = "",
        annotations: dict[str, bool] | None = None,
        tags: set[str] | None = None,
    ) -> t.Callable[[t.Callable[..., t.Any]], t.Callable[..., t.Any]]:
        """Match ``FastMCP.tool()`` decorator behavior for capture."""
        annotations = annotations or {}
        tags = tags or set()

        def decorator(func: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
            if TAG_DESTRUCTIVE in tags:
                safety = "destructive"
            elif TAG_MUTATING in tags:
                safety = "mutating"
            else:
                safety = "readonly"

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
                    safety=safety,
                    annotations=annotations,
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


def _tool_from_callable(
    func: t.Callable[..., t.Any],
    *,
    module_name: str,
    area_map: dict[str, str],
) -> ToolInfo | None:
    """Build ``ToolInfo`` from a decorated function (``__fastmcp__``)."""
    meta = getattr(func, "__fastmcp__", None)
    if meta is None:
        return None
    tags = getattr(meta, "tags", None) or set()
    if not isinstance(tags, set):
        tags = set(tags) if tags else set()
    if TAG_DESTRUCTIVE in tags:
        safety = "destructive"
    elif TAG_MUTATING in tags:
        safety = "mutating"
    else:
        safety = "readonly"
    area = area_map.get(module_name, module_name.replace("_tools", ""))
    name = getattr(meta, "name", None) or func.__name__
    title = getattr(meta, "title", None) or name.replace("_", " ").title()
    annotations = getattr(meta, "annotations", None)
    ann_dict: dict[str, bool] = {}
    if annotations is not None:
        for field in (
            "readOnlyHint",
            "destructiveHint",
            "idempotentHint",
            "openWorldHint",
        ):
            val = getattr(annotations, field, None)
            if isinstance(val, bool):
                ann_dict[field] = val
    return ToolInfo(
        name=name,
        title=title,
        module_name=module_name,
        area=area,
        safety=safety,
        annotations=ann_dict,
        func=func,
        docstring=func.__doc__ or "",
        params=extract_params(func),
        return_annotation=normalize_annotation_text(
            inspect.signature(func).return_annotation,
        ),
    )


def collect_tools(app: Sphinx) -> None:
    """Populate ``app.env.fastmcp_tools`` from configured modules."""
    modules: list[str] = list(app.config.fastmcp_tool_modules)
    area_map: dict[str, str] = dict(app.config.fastmcp_area_map)
    mode = str(app.config.fastmcp_collector_mode)
    if mode not in ("register", "introspect"):
        logger.warning(
            "sphinx_autodoc_fastmcp: unknown fastmcp_collector_mode %r; using 'register'",
            mode,
        )
        mode = "register"

    if not modules:
        logger.warning(
            "sphinx_autodoc_fastmcp: fastmcp_tool_modules is empty; no tools collected",
        )
        app.env.fastmcp_tools = {}  # type: ignore[attr-defined]
        return

    collector_tools: list[ToolInfo] = []

    if mode == "register":
        collector = ToolCollector(area_map=area_map)
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
                )
                if info is not None:
                    collector_tools.append(info)

    app.env.fastmcp_tools = {tool.name: tool for tool in collector_tools}  # type: ignore[attr-defined]


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
    # If the instance has no components yet, try to run the server's
    # register-all hook so autodoc sees the same surface a live server does.
    provider = getattr(obj, "local_provider", None)
    if provider is not None:
        components = getattr(provider, "_components", None)
        if not components:
            for hook_name in ("register_all", "_register_all"):
                hook = getattr(mod, hook_name, None)
                if callable(hook):
                    try:
                        hook()
                    except Exception:  # pragma: no cover - defensive
                        logger.warning(
                            "sphinx_autodoc_fastmcp: %s.%s() raised",
                            module_path,
                            hook_name,
                            exc_info=True,
                        )
                    break
    return obj


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


_SCHEMA_NOTE_MARKER = "Provide as a JSON string matching the following schema:"


def _strip_schema_note(text: str) -> str:
    r"""Remove FastMCP's auto-appended JSON-schema hint from a description.

    FastMCP's prompt argument builder tacks on
    ``"\n\nProvide as a JSON string matching the following schema: {...}"``
    to help LLMs; it's noise in human-facing docs.

    Examples
    --------
    >>> _strip_schema_note("Summary.")
    'Summary.'
    >>> _strip_schema_note("Summary.\n\nProvide as a JSON string matching the following schema: {}")
    'Summary.'
    """
    idx = text.find(_SCHEMA_NOTE_MARKER)
    if idx == -1:
        return text.strip()
    return text[:idx].rstrip().rstrip("\n").strip()


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
        for field_name in (
            "audience",
            "priority",
            "lastModified",
        ):
            val = getattr(annotations, field_name, None)
            if val is not None:
                ann_dict[field_name] = val
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
        for field_name in ("audience", "priority", "lastModified"):
            val = getattr(annotations, field_name, None)
            if val is not None:
                ann_dict[field_name] = val
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
            except Exception:  # pragma: no cover - defensive
                logger.warning(
                    "sphinx_autodoc_fastmcp: could not import fastmcp types",
                    exc_info=True,
                )
                _Prompt = _Resource = _ResourceTemplate = None

            if _Prompt is not None:
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
                        prompts[info_p.name] = info_p

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
