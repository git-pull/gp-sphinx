"""Doctree transforms for componentized autodoc layout.

Runs as a ``doctree-resolved`` event handler after
``sphinx-autodoc-api-style``. It rebuilds Python autodoc entries into
stable ``api-*`` wrappers while preserving Sphinx's outer ``dl / dt / dd``
structure.

Examples
--------
>>> from sphinx_autodoc_layout._transforms import _classify_child
>>> from docutils import nodes
>>> _classify_child(nodes.paragraph())
'narrative'
>>> _classify_child(nodes.field_list())
'fields'
"""

from __future__ import annotations

import typing as t

from docutils import nodes
from sphinx import addnodes

from sphinx_autodoc_layout._nodes import (
    api_component,
    api_inline_component,
    api_permalink,
    gal_fold,
    gal_region,
    gal_sig_fold,
)

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

_SECTION_COMPONENTS: dict[str, str] = {
    "narrative": "api-description",
    "fields": "api-parameters",
    "members": "api-footer",
}

_SKIP_FOLD_OBJTYPES: frozenset[str] = frozenset(
    {
        "attribute",
        "data",
        "fixture",
        "module",
        "property",
    }
)

_MEMBER_CONTAINER_OBJTYPES: frozenset[str] = frozenset({"class", "exception"})


def _append_class(node: nodes.Element, class_name: str) -> None:
    """Append *class_name* to ``node['classes']`` if needed."""
    classes = list(node.get("classes", []))
    if class_name not in classes:
        classes.append(class_name)
    node["classes"] = classes


def _make_api_component(
    name: str,
    *,
    tag: str = "div",
    classes: tuple[str, ...] = (),
    html_attrs: dict[str, str] | None = None,
) -> api_component:
    """Create an ``api_component`` node with stable DOM classes.

    Parameters
    ----------
    name : str
        Public component class name.
    tag : str
        HTML tag emitted by the visitor.
    classes : tuple[str, ...]
        Extra compatibility classes.
    html_attrs : dict[str, str] | None
        Extra HTML attributes for the rendered tag.

    Returns
    -------
    api_component
        A configured component wrapper.

    Examples
    --------
    >>> wrapper = _make_api_component("api-content", classes=("legacy",))
    >>> wrapper.get("classes")
    ['api-content', 'legacy']
    """
    component = api_component(name=name, tag=tag)
    component["classes"] = [name, *classes]
    if html_attrs:
        component["html_attrs"] = html_attrs
    return component


def _make_api_inline_component(
    name: str,
    *,
    tag: str = "span",
    classes: tuple[str, ...] = (),
    html_attrs: dict[str, str] | None = None,
) -> api_inline_component:
    """Create an inline API wrapper for text-compatible header content."""
    component = api_inline_component(name=name, tag=tag)
    component["classes"] = [name, *classes]
    if html_attrs:
        component["html_attrs"] = html_attrs
    return component


def _make_api_permalink(desc_sig: addnodes.desc_signature) -> api_permalink | None:
    """Create the managed permalink node for a signature."""
    ids = list(desc_sig.get("ids", []))
    if not ids:
        return None
    link = api_permalink(
        href=f"#{ids[0]}",
        title="Link to this definition",
    )
    link["classes"] = ["headerlink", "api-link"]
    return link


def _primary_signature_id(desc_node: addnodes.desc) -> str | None:
    """Return the first signature id for a ``desc`` node."""
    for child in desc_node.children:
        if isinstance(child, addnodes.desc_signature):
            ids = list(child.get("ids", []))
            if ids:
                return ids[0]
    return None


def _classify_child(child: nodes.Node) -> str:
    """Classify a ``desc_content`` child by its node type.

    Parameters
    ----------
    child : nodes.Node
        A direct child of ``desc_content``.

    Returns
    -------
    str
        One of ``"fields"``, ``"members"``, or ``"narrative"``.

    Examples
    --------
    >>> from docutils import nodes
    >>> from sphinx import addnodes
    >>> _classify_child(nodes.field_list())
    'fields'
    >>> _classify_child(addnodes.desc())
    'members'
    >>> _classify_child(nodes.note())
    'narrative'
    """
    if isinstance(child, nodes.field_list):
        return "fields"
    if isinstance(child, addnodes.desc):
        return "members"
    return "narrative"


def _component_name_for_kind(kind: str) -> str:
    """Return the public API section name for a legacy kind string."""
    return _SECTION_COMPONENTS[kind]


def _wrap_content_runs(desc_node: addnodes.desc) -> None:
    """Wrap contiguous ``desc_content`` runs in explicit API sections.

    Parameters
    ----------
    desc_node : addnodes.desc
        The description node to restructure.

    Examples
    --------
    >>> from docutils import nodes
    >>> from sphinx import addnodes
    >>> desc = addnodes.desc(domain="py", objtype="function")
    >>> desc += addnodes.desc_signature()
    >>> content = addnodes.desc_content()
    >>> content += nodes.paragraph("", "hello")
    >>> content += nodes.field_list()
    >>> desc += content
    >>> _wrap_content_runs(desc)
    >>> [child.get("name") for child in content.children]
    ['api-description', 'api-parameters']
    """
    content = next(
        (c for c in desc_node.children if isinstance(c, addnodes.desc_content)),
        None,
    )
    if content is None:
        return

    _append_class(content, "api-content")
    if not content.children:
        return

    original = list(content.children)
    content.children = []

    current_kind: str | None = None
    current_section: api_component | None = None

    for child in original:
        kind = _classify_child(child)
        if kind != current_kind:
            if current_section is not None:
                content += current_section
            current_section = _make_api_component(
                _component_name_for_kind(kind),
                classes=("gal-region", f"gal-region--{kind}"),
            )
            current_kind = kind
        assert current_section is not None
        current_section += child

    if current_section is not None:
        content += current_section


def _ensure_desc_content(desc_node: addnodes.desc) -> addnodes.desc_content:
    """Return an existing ``desc_content`` child or create one."""
    for child in desc_node.children:
        if isinstance(child, addnodes.desc_content):
            return child
    content = addnodes.desc_content()
    desc_node += content
    return content


def _is_member_desc_for_container(
    member_desc: addnodes.desc,
    *,
    container_id: str,
) -> bool:
    """Return ``True`` when *member_desc* belongs to *container_id*."""
    member_id = _primary_signature_id(member_desc)
    if member_id is None:
        return False
    return member_id.startswith(f"{container_id}.")


def _nest_python_members(container: nodes.Element) -> None:
    """Move sibling Python member descriptions into their parent class.

    Examples
    --------
    >>> from docutils import nodes
    >>> from sphinx import addnodes
    >>> parent = nodes.section()
    >>> klass = addnodes.desc(domain="py", objtype="class")
    >>> klass += addnodes.desc_signature(ids=["demo.Widget"])
    >>> klass += addnodes.desc_content()
    >>> method = addnodes.desc(domain="py", objtype="method")
    >>> method += addnodes.desc_signature(ids=["demo.Widget.run"])
    >>> method += addnodes.desc_content()
    >>> parent += klass
    >>> parent += method
    >>> _nest_python_members(parent)
    >>> len(parent.children)
    1
    >>> len(klass[-1].children)
    1
    """
    index = 0
    while index < len(container.children):
        child = container.children[index]

        if isinstance(child, nodes.Element):
            _nest_python_members(child)

        if not isinstance(child, addnodes.desc):
            index += 1
            continue
        if child.get("domain") != "py":
            index += 1
            continue
        if child.get("objtype") not in _MEMBER_CONTAINER_OBJTYPES:
            index += 1
            continue

        container_id = _primary_signature_id(child)
        if container_id is None:
            index += 1
            continue

        content = _ensure_desc_content(child)

        while index + 1 < len(container.children):
            sibling = container.children[index + 1]
            if not isinstance(sibling, addnodes.desc):
                break
            if sibling.get("domain") != "py":
                break
            if not _is_member_desc_for_container(sibling, container_id=container_id):
                break

            container.remove(sibling)
            content += sibling

        index += 1


def _count_field_entries(field_list: nodes.field_list) -> int:
    """Count individual entries in a Sphinx field list.

    Parameters
    ----------
    field_list : nodes.field_list
        The field list to count.

    Returns
    -------
    int
        Total entry count.
    """
    count = 0
    for field in field_list.children:
        if not isinstance(field, nodes.field):
            continue
        for body_child in field.children:
            if isinstance(body_child, nodes.field_body):
                for item in body_child.children:
                    if isinstance(item, nodes.bullet_list):
                        count += sum(
                            1 for li in item.children if isinstance(li, nodes.list_item)
                        )
                        break
                else:
                    count += 1
                break
        else:
            count += 1
    return count


def _is_parameters_section(node: nodes.Node) -> bool:
    """Return ``True`` when *node* is an API parameters section."""
    if isinstance(node, api_component):
        return node.get("name") == "api-parameters"
    if isinstance(node, gal_region):
        return node.get("kind") == "fields"
    return False


def _fold_large_field_regions(
    content: addnodes.desc_content,
    threshold: int,
) -> None:
    """Wrap large field-list regions in ``gal_fold`` disclosure blocks."""
    for section in content.children:
        if not _is_parameters_section(section):
            continue
        assert isinstance(section, nodes.Element)
        for field_list in list(section.children):
            if not isinstance(field_list, nodes.field_list):
                continue
            entry_count = _count_field_entries(field_list)
            if entry_count < threshold:
                continue
            fold = gal_fold(
                kind="parameters",
                summary=f"Parameters ({entry_count})",
            )
            idx = section.children.index(field_list)
            section.remove(field_list)
            fold += field_list
            section.insert(idx, fold)


def _is_viewcode_ref(node: nodes.Node) -> bool:
    """Return ``True`` when *node* is a viewcode/source reference."""
    return isinstance(node, nodes.reference) and any(
        "viewcode-link" in getattr(child, "get", lambda *_: [])("classes", [])
        for child in node.children
        if isinstance(child, nodes.inline)
    )


def _count_signature_parameters(
    parameter_list: addnodes.desc_parameterlist,
) -> tuple[str, int]:
    """Return the first parameter text and total parameter count."""
    params = list(parameter_list.findall(addnodes.desc_parameter))
    first = params[0].astext().strip() if params else ""
    return first, len(params)


def _signature_panel_id(desc_sig: addnodes.desc_signature) -> str:
    """Return the stable DOM id for an expanded signature panel."""
    ids = list(desc_sig.get("ids", []))
    base = ids[0] if ids else "api-signature"
    return f"{base}--signature-panel"


def _extract_toolbar_content(
    toolbar: nodes.inline | None,
) -> tuple[list[nodes.Node], nodes.reference | None]:
    """Split toolbar content into badge-side children and source link."""
    badge_children: list[nodes.Node] = []
    source_ref: nodes.reference | None = None

    if toolbar is None:
        return badge_children, source_ref

    for child in list(toolbar.children):
        if source_ref is None and _is_viewcode_ref(child):
            assert isinstance(child, nodes.reference)
            source_ref = child
            continue
        badge_children.append(child)

    return badge_children, source_ref


def _rebuild_signature_layout(
    desc_sig: addnodes.desc_signature,
    *,
    threshold: int,
    include_permalink: bool,
) -> None:
    """Rebuild a signature into explicit API header subcomponents."""
    if desc_sig.get("is_multiline"):
        return

    original = list(desc_sig.children)
    desc_sig.children = []

    toolbar: nodes.inline | None = None
    row_children: list[nodes.Node] = []
    fallback_source_ref: nodes.reference | None = None

    for child in original:
        if isinstance(child, nodes.inline) and "gas-toolbar" in child.get(
            "classes", []
        ):
            toolbar = child
            continue
        if isinstance(child, nodes.reference) and "headerlink" in child.get(
            "classes", []
        ):
            continue
        if fallback_source_ref is None and _is_viewcode_ref(child):
            assert isinstance(child, nodes.reference)
            fallback_source_ref = child
            continue
        row_children.append(child)

    badge_children, source_ref = _extract_toolbar_content(toolbar)
    if source_ref is None:
        source_ref = fallback_source_ref

    layout = _make_api_component("api-layout")
    left = _make_api_component("api-layout-left")
    signature = _make_api_component("api-signature")
    right = _make_api_component("api-layout-right", classes=("gas-toolbar",))

    panel: api_component | None = None
    folded = False

    for child in row_children:
        if not folded and isinstance(child, addnodes.desc_parameterlist):
            first_param, param_count = _count_signature_parameters(child)
            if param_count >= threshold:
                panel_id = _signature_panel_id(desc_sig)
                signature += gal_sig_fold(
                    first_param=first_param,
                    param_count=param_count,
                    panel_id=panel_id,
                )
                panel = _make_api_component(
                    "api-signature-panel",
                    classes=("gal-sig-panel",),
                    html_attrs={
                        "aria-hidden": "true",
                        "data-expanded": "false",
                        "hidden": "hidden",
                        "id": panel_id,
                    },
                )
                panel += child
                folded = True
                continue
        signature += child

    if include_permalink:
        permalink = _make_api_permalink(desc_sig)
        if permalink is not None:
            signature += permalink

    left += signature
    if panel is not None:
        left += panel

    if badge_children:
        badge_container = _make_api_inline_component("api-badge-container")
        for child in badge_children:
            badge_container += child
        right += badge_container

    if source_ref is not None:
        source_container = _make_api_inline_component("api-source-link")
        source_container += source_ref
        right += source_container

    layout += left
    layout += right
    desc_sig += layout


def on_doctree_resolved(
    app: Sphinx,
    doctree: nodes.document,
    docname: str,
) -> None:
    """Restructure Python autodoc output into stable API components.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application.
    doctree : nodes.document
        The resolved doctree.
    docname : str
        The document name.
    """
    if not app.config.gal_enabled:
        return
    if getattr(app.builder, "format", "") != "html":
        return

    threshold: int = app.config.gal_collapsed_threshold
    fold_params: bool = app.config.gal_fold_parameters
    include_permalink = bool(
        app.config.html_permalinks and getattr(app.builder, "add_permalinks", False)
    )

    _nest_python_members(doctree)

    for desc_node in doctree.findall(addnodes.desc):
        if desc_node.get("domain") != "py":
            continue

        _append_class(desc_node, "api-container")
        _wrap_content_runs(desc_node)

        objtype = desc_node.get("objtype", "")
        allow_signature_fold = fold_params and objtype not in _SKIP_FOLD_OBJTYPES

        for child in desc_node.children:
            if not isinstance(child, addnodes.desc_signature):
                continue
            _append_class(child, "api-header")
            child["api_managed"] = not child.get("is_multiline", False)
            _rebuild_signature_layout(
                child,
                threshold=threshold if allow_signature_fold else 10**9,
                include_permalink=include_permalink,
            )

        if not allow_signature_fold:
            continue

        content = next(
            (c for c in desc_node.children if isinstance(c, addnodes.desc_content)),
            None,
        )
        if content is not None:
            _fold_large_field_regions(content, threshold)
