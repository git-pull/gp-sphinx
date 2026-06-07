"""Shared rendering pipeline for docutils component autodoc entries.

Every component type (transform, reader, parser, writer, node,
translator) renders through the same three steps:

1. :func:`component_markup` builds ``.. docutils:<objtype>::`` markup
   so parsed ``desc`` nodes natively carry ``domain="docutils"``.
2. :func:`inject_component_badges` attaches the kind badge group to
   each signature.
3. :func:`normalize_component_nodes` inserts the shared fact rows after
   the summary paragraphs.

:func:`render_component_nodes` chains all three for the ``Auto*``
directives.
"""

from __future__ import annotations

import importlib
import inspect
import typing as t

from sphinx import addnodes

from sphinx_autodoc_docutils._directives import (
    _content_node,
    _insert_after_summary,
    _module_members,
)
from sphinx_ux_autodoc_layout import (
    build_api_facts_section,
    build_chip_paragraph,
    build_linked_literal,
    inject_signature_slots,
    iter_desc_nodes,
    parse_generated_markup,
)

if t.TYPE_CHECKING:
    from docutils import nodes
    from sphinx.util.docutils import SphinxDirective

    from sphinx_ux_autodoc_layout import ApiFactRow

_T = t.TypeVar("_T")


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
    ...     "transform",
    ...     "pkg.transforms.Sanitize",
    ...     "Strip unsafe nodes.",
    ... )
    >>> ".. docutils:transform:: pkg.transforms.Sanitize" in markup
    True
    >>> "Strip unsafe nodes." in markup
    True
    >>> ":no-index:" in component_markup("node", "pkg.icon", "", no_index=True)
    True
    """
    return "\n".join(
        [
            f".. docutils:{objtype}:: {path}",
            "   :no-index:" if no_index else "",
            "",
            f"   {summary or f'Autodocumented docutils {objtype}.'}",
        ],
    )


def component_classes(
    module_name: str,
    base: type[_T],
) -> list[type[_T]]:
    """Return public subclasses of *base* defined directly in a module.

    The base class itself is excluded even when re-exported, so passing
    ``docutils.transforms`` never surfaces ``Transform`` as a documented
    component.

    Examples
    --------
    >>> from docutils.transforms import Transform
    >>> classes = component_classes("docutils.transforms.misc", Transform)
    >>> sorted(cls.__name__ for cls in classes)
    ['CallBack', 'ClassAttribute', 'Transitions']

    >>> component_classes("sphinx_fonts", Transform)
    []
    """
    importlib.import_module(module_name)
    results: list[type[_T]] = []
    for _name, value in _module_members(module_name):
        if inspect.isclass(value) and issubclass(value, base) and value is not base:
            results.append(value)
    return results


def inject_component_badges(
    node_list: list[nodes.Node],
    *,
    objtype: str,
    badge_group: nodes.inline,
) -> None:
    """Attach shared badge-slot metadata to parsed ``docutils:*`` entries.

    Examples
    --------
    >>> from sphinx import addnodes
    >>> from sphinx_autodoc_docutils._badges import build_kind_badge_group
    >>> desc = addnodes.desc(domain="docutils", objtype="transform")
    >>> sig = addnodes.desc_signature()
    >>> desc += sig
    >>> inject_component_badges(
    ...     [desc],
    ...     objtype="transform",
    ...     badge_group=build_kind_badge_group("transform"),
    ... )
    >>> sig["sadoc_badges_injected"]
    True

    Entries of another objtype are left untouched:

    >>> other = addnodes.desc(domain="docutils", objtype="writer")
    >>> other_sig = addnodes.desc_signature()
    >>> other += other_sig
    >>> inject_component_badges(
    ...     [other],
    ...     objtype="transform",
    ...     badge_group=build_kind_badge_group("transform"),
    ... )
    >>> other_sig.get("sadoc_badges_injected") is None
    True
    """
    for desc_node in iter_desc_nodes(node_list):
        if desc_node.get("domain") != "docutils" or desc_node.get("objtype") != objtype:
            continue
        for sig_node in desc_node.children:
            if not isinstance(sig_node, addnodes.desc_signature):
                continue
            inject_signature_slots(
                sig_node,
                marker_attr="sadoc_badges_injected",
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
    >>> from docutils import nodes as docutils_nodes
    >>> from sphinx import addnodes
    >>> from sphinx_ux_autodoc_layout import ApiFactRow
    >>> desc = addnodes.desc(domain="docutils", objtype="transform")
    >>> desc += addnodes.desc_signature()
    >>> content = addnodes.desc_content()
    >>> content += docutils_nodes.paragraph("", "Summary.")
    >>> desc += content
    >>> body = docutils_nodes.paragraph()
    >>> body += docutils_nodes.literal("demo", "demo")
    >>> normalize_component_nodes(
    ...     [desc],
    ...     objtype="transform",
    ...     fact_rows=[ApiFactRow("Python path", body)],
    ... )
    >>> content.children[1].get("name")
    'gp-sphinx-api-facts'
    """
    for desc_node in iter_desc_nodes(node_list):
        if desc_node.get("domain") != "docutils" or desc_node.get("objtype") != objtype:
            continue
        content = _content_node(desc_node)
        if content is None:
            continue
        _insert_after_summary(content, build_api_facts_section(fact_rows))


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


def safe_transform_classes(component_cls: type) -> list[type]:
    """Return transform classes from ``cls().get_transforms()``, guarded.

    Readers and writers expose their transform set through
    ``get_transforms()`` on an *instance*; real-world components (e.g.
    django-docutils) may need framework state to instantiate or to
    resolve their transform list, so any failure degrades to ``[]``
    rather than breaking the docs build.

    Examples
    --------
    >>> from docutils.readers.standalone import Reader
    >>> classes = safe_transform_classes(Reader)
    >>> any(cls.__name__ == "Transitions" for cls in classes)
    True

    >>> safe_transform_classes(object)
    []
    """
    try:
        transforms = component_cls().get_transforms()
    except Exception:  # noqa: BLE001 — degrade to no facts on any component error
        return []
    return list(transforms)


def linked_paragraph(target: str, display: str | None = None) -> nodes.paragraph:
    """Return a paragraph holding one linked literal chip.

    Examples
    --------
    >>> linked_paragraph("pkg.mod.Cls").astext()
    'pkg.mod.Cls'
    >>> linked_paragraph("pkg.mod.Cls", "Cls").astext()
    'Cls'
    """
    return build_chip_paragraph([build_linked_literal(target, display)])


def transform_chip_nodes(component_cls: type) -> list[nodes.Node]:
    """Return linked chips for a component's transform set.

    Each chip displays the bare class name and cross-references the
    fully-qualified path, so transforms documented anywhere in the
    project become links while docutils-internal transforms stay plain
    chips.

    Examples
    --------
    >>> from docutils.readers.standalone import Reader
    >>> chips = transform_chip_nodes(Reader)
    >>> any(chip.astext() == "Transitions" for chip in chips)
    True
    """
    return [
        build_linked_literal(
            f"{transform_cls.__module__}.{transform_cls.__qualname__}",
            transform_cls.__name__,
        )
        for transform_cls in safe_transform_classes(component_cls)
    ]


def import_component(path: str) -> type:
    """Import one component class from a dotted ``module.ClassName`` path.

    Examples
    --------
    >>> cls = import_component("docutils.transforms.misc.Transitions")
    >>> cls.__name__
    'Transitions'
    """
    module_name, _, attr_name = path.rpartition(".")
    value = getattr(importlib.import_module(module_name), attr_name)
    if not inspect.isclass(value):
        msg = f"Expected a class at {path!r}, got {type(value).__name__}"
        raise TypeError(msg)
    return t.cast("type", value)
