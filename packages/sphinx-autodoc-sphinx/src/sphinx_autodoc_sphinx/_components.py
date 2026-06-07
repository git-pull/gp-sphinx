"""Shared rendering pipeline for Sphinx extension component entries.

Mirrors ``sphinx_autodoc_docutils._components`` for this package's
component types (builders, domains): markup generation targeting the
``sphinxext`` domain, badge injection, and fact-section insertion. Kept
self-contained so the package installs standalone without a dependency
on its docutils sibling.
"""

from __future__ import annotations

import functools
import importlib
import inspect
import logging
import typing as t

from docutils import nodes
from sphinx import addnodes

from sphinx_autodoc_sphinx._directives import RecorderApp
from sphinx_ux_autodoc_layout import (
    build_api_facts_section,
    inject_signature_slots,
    iter_desc_nodes,
    parse_generated_markup,
)

if t.TYPE_CHECKING:
    from sphinx.util.docutils import SphinxDirective

    from sphinx_ux_autodoc_layout import ApiFactRow

logger = logging.getLogger(__name__)

_T = t.TypeVar("_T")


@functools.cache
def replay_setup(module_name: str) -> RecorderApp | None:
    """Run a module's ``setup()`` against a recorder; None on failure.

    Cached for the same reason as the docutils-side replay: a docs
    build invokes discovery once per directive call, and re-importing
    plus re-replaying each package's ``setup()`` would repeat work.
    Consumers iterate ``recorder.calls`` and never mutate it.

    Examples
    --------
    >>> recorder = replay_setup("sphinx_fonts")
    >>> any(name == "add_config_value" for name, _, _ in recorder.calls)
    True

    >>> replay_setup("sphinx_autodoc_sphinx._components") is None
    True
    """
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return None
    setup_fn = getattr(module, "setup", None)
    if not callable(setup_fn):
        return None
    recorder = RecorderApp()
    try:
        setup_fn(recorder)
    except Exception:
        logger.debug(
            "setup replay failed for %s; falling back to module introspection",
            module_name,
            exc_info=True,
        )
        return None
    return recorder


def component_markup(
    objtype: str,
    path: str,
    summary: str,
    *,
    no_index: bool = False,
) -> str:
    """Return reStructuredText markup documenting one component class.

    Examples
    --------
    >>> markup = component_markup(
    ...     "builder",
    ...     "pkg.builders.ZipBuilder",
    ...     "Bundle output into a zip archive.",
    ... )
    >>> ".. sphinxext:builder:: pkg.builders.ZipBuilder" in markup
    True
    >>> ":no-index:" in component_markup("domain", "pkg.D", "", no_index=True)
    True
    """
    return "\n".join(
        [
            f".. sphinxext:{objtype}:: {path}",
            "   :no-index:" if no_index else "",
            "",
            f"   {summary or f'Autodocumented Sphinx {objtype}.'}",
        ],
    )


def component_classes(
    module_name: str,
    base: type[_T],
) -> list[type[_T]]:
    """Return public subclasses of *base* defined directly in a module.

    Examples
    --------
    >>> from sphinx.builders import Builder
    >>> classes = component_classes("sphinx.builders.dummy", Builder)
    >>> [cls.__name__ for cls in classes]
    ['DummyBuilder']

    >>> component_classes("sphinx_fonts", Builder)
    []
    """
    module = importlib.import_module(module_name)
    results: list[type[_T]] = []
    for name, value in inspect.getmembers(module):
        if (
            not name.startswith("_")
            and inspect.isclass(value)
            and getattr(value, "__module__", None) == module.__name__
            and issubclass(value, base)
            and value is not base
        ):
            results.append(value)
    return results


def component_summary(value: object) -> str:
    """Return the first summary line for a Python object.

    ``inspect.getdoc`` falls back to inherited docstrings, so
    undocumented subclasses summarize via their base class.

    Examples
    --------
    >>> from sphinx.builders.dummy import DummyBuilder
    >>> component_summary(DummyBuilder)
    'Builds target formats from the reST sources.'
    """
    doc = inspect.getdoc(value) or ""
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def import_component(path: str) -> type:
    """Import one component class from a dotted ``module.ClassName`` path.

    Examples
    --------
    >>> import_component("sphinx.builders.dummy.DummyBuilder").__name__
    'DummyBuilder'
    """
    module_name, _, attr_name = path.rpartition(".")
    value = getattr(importlib.import_module(module_name), attr_name)
    if not inspect.isclass(value):
        msg = f"Expected a class at {path!r}, got {type(value).__name__}"
        raise TypeError(msg)
    return t.cast("type", value)


def inject_component_badges(
    node_list: list[nodes.Node],
    *,
    objtype: str,
    badge_group: nodes.inline,
) -> None:
    """Attach shared badge-slot metadata to parsed ``sphinxext:*`` entries.

    Examples
    --------
    >>> from sphinx_autodoc_sphinx._badges import build_builder_badge_group
    >>> desc = addnodes.desc(domain="sphinxext", objtype="builder")
    >>> sig = addnodes.desc_signature()
    >>> desc += sig
    >>> inject_component_badges(
    ...     [desc],
    ...     objtype="builder",
    ...     badge_group=build_builder_badge_group("zip"),
    ... )
    >>> sig["sas_badges_injected"]
    True

    Entries of another objtype are left untouched:

    >>> other = addnodes.desc(domain="sphinxext", objtype="domain")
    >>> other_sig = addnodes.desc_signature()
    >>> other += other_sig
    >>> inject_component_badges(
    ...     [other],
    ...     objtype="builder",
    ...     badge_group=build_builder_badge_group("zip"),
    ... )
    >>> other_sig.get("sas_badges_injected") is None
    True
    """
    for desc_node in iter_desc_nodes(node_list):
        if (
            desc_node.get("domain") != "sphinxext"
            or desc_node.get("objtype") != objtype
        ):
            continue
        for sig_node in desc_node.children:
            if not isinstance(sig_node, addnodes.desc_signature):
                continue
            inject_signature_slots(
                sig_node,
                marker_attr="sas_badges_injected",
                badge_node=badge_group.deepcopy(),
                extract_source_link=False,
            )


def normalize_component_nodes(
    node_list: list[nodes.Node],
    *,
    objtype: str,
    fact_rows: list[ApiFactRow],
) -> None:
    """Attach the shared facts section to parsed component entries.

    The facts section lands directly after the leading summary
    paragraphs inside ``desc_content``.

    Examples
    --------
    >>> from sphinx_ux_autodoc_layout import ApiFactRow
    >>> desc = addnodes.desc(domain="sphinxext", objtype="builder")
    >>> desc += addnodes.desc_signature()
    >>> content = addnodes.desc_content()
    >>> content += nodes.paragraph("", "Summary.")
    >>> desc += content
    >>> body = nodes.paragraph()
    >>> body += nodes.literal("demo", "demo")
    >>> normalize_component_nodes(
    ...     [desc],
    ...     objtype="builder",
    ...     fact_rows=[ApiFactRow("Python path", body)],
    ... )
    >>> content.children[1].get("name")
    'gp-sphinx-api-facts'
    """
    for desc_node in iter_desc_nodes(node_list):
        if (
            desc_node.get("domain") != "sphinxext"
            or desc_node.get("objtype") != objtype
        ):
            continue
        content = next(
            (
                child
                for child in desc_node.children
                if isinstance(child, addnodes.desc_content)
            ),
            None,
        )
        if content is None:
            continue
        insert_idx = 0
        while insert_idx < len(content.children) and isinstance(
            content.children[insert_idx],
            nodes.paragraph,
        ):
            insert_idx += 1
        content.insert(insert_idx, build_api_facts_section(fact_rows))


def render_component_nodes(
    directive: SphinxDirective,
    *,
    objtype: str,
    path: str,
    summary: str,
    fact_rows: list[ApiFactRow],
    badge_group: nodes.inline,
    no_index: bool = False,
) -> list[nodes.Node]:
    """Render one component entry with badges and facts attached."""
    node_list = parse_generated_markup(
        directive,
        component_markup(objtype, path, summary, no_index=no_index),
    )
    inject_component_badges(node_list, objtype=objtype, badge_group=badge_group)
    normalize_component_nodes(node_list, objtype=objtype, fact_rows=fact_rows)
    return node_list
