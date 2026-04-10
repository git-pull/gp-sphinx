"""Collect FastMCP tool metadata at Sphinx build time."""

from __future__ import annotations

import importlib
import inspect
import logging
import typing as t

from sphinx.application import Sphinx
from sphinx_typehints_gp import normalize_annotation_text

from sphinx_autodoc_fastmcp._models import ToolInfo
from sphinx_autodoc_fastmcp._parsing import extract_params

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
