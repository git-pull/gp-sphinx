"""Doctree transforms for componentized autodoc layout.

Runs as a ``doctree-resolved`` event handler after
``sphinx-autodoc-api-style``. It rebuilds managed Sphinx object entries into
stable ``gp-sphinx-api-*`` wrappers while preserving Sphinx's outer
``dl / dt / dd`` structure.

Examples
--------
>>> from sphinx_ux_autodoc_layout._transforms import _classify_child
>>> from docutils import nodes
>>> _classify_child(nodes.paragraph())
'narrative'
>>> _classify_child(nodes.field_list())
'fields'
"""

from __future__ import annotations

import dataclasses
import typing as t

from docutils import nodes
from sphinx import addnodes

from sphinx_ux_autodoc_layout._css import API
from sphinx_ux_autodoc_layout._nodes import (
    api_component,
    api_fold,
    api_permalink,
    api_region,
    api_sig_fold,
    api_slot,
    build_api_component,
    build_api_inline_component,
)
from sphinx_ux_autodoc_layout._slots import is_viewcode_ref
from sphinx_ux_badges import SAB

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

_SECTION_COMPONENTS: dict[str, str] = {
    "narrative": API.DESCRIPTION,
    "facts": API.FACTS,
    "fields": API.PARAMETERS,
    "options": API.OPTIONS,
    "members": API.FOOTER,
}

_STRUCTURED_SECTION_NAMES: frozenset[str] = frozenset(_SECTION_COMPONENTS.values())

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

_MANAGED_PYTHON_OBJTYPES: tuple[str, ...] = (
    "attribute",
    "class",
    "classmethod",
    "data",
    "exception",
    "fixture",
    "function",
    "method",
    "module",
    "property",
    "staticmethod",
    "type",
)


@dataclasses.dataclass(frozen=True, slots=True)
class DescLayoutProfile:
    """Typed layout policy for a managed ``addnodes.desc`` entry."""

    domain: str
    objtype: str
    slug: str
    allow_signature_fold: bool = False

    @property
    def class_name(self) -> str:
        """Return the stable CSS class for the profile."""
        return API.profile(self.slug)


_PROFILE_REGISTRY: dict[tuple[str, str], DescLayoutProfile] = {
    **{
        ("py", objtype): DescLayoutProfile(
            domain="py",
            objtype=objtype,
            slug=f"py-{objtype.replace(':', '-')}",
            allow_signature_fold=objtype not in _SKIP_FOLD_OBJTYPES,
        )
        for objtype in _MANAGED_PYTHON_OBJTYPES
    },
    ("std", "confval"): DescLayoutProfile(
        domain="std",
        objtype="confval",
        slug="confval",
    ),
    ("rst", "directive"): DescLayoutProfile(
        domain="rst",
        objtype="directive",
        slug="rst-directive",
    ),
    ("rst", "role"): DescLayoutProfile(
        domain="rst",
        objtype="role",
        slug="rst-role",
    ),
    ("rst", "directive:option"): DescLayoutProfile(
        domain="rst",
        objtype="directive:option",
        slug="rst-directive-option",
    ),
    ("mcp", "tool"): DescLayoutProfile(
        domain="mcp",
        objtype="tool",
        slug="mcp-tool",
        allow_signature_fold=True,
    ),
}


def _append_class(node: nodes.Element, class_name: str) -> None:
    """Append *class_name* to ``node['classes']`` if needed."""
    classes = list(node.get("classes", []))
    if class_name not in classes:
        classes.append(class_name)
    node["classes"] = classes


def _desc_layout_profile(desc_node: addnodes.desc) -> DescLayoutProfile | None:
    """Return the layout profile for a managed description node."""
    domain = str(desc_node.get("domain", ""))
    objtype = str(desc_node.get("objtype", ""))
    return _PROFILE_REGISTRY.get((domain, objtype))


def _make_api_permalink(desc_sig: addnodes.desc_signature) -> api_permalink | None:
    """Create the managed permalink node for a signature."""
    ids: list[str] = [
        str(node_id) for node_id in t.cast(list[t.Any], desc_sig.get("ids", []))
    ]
    if not ids:
        return None
    link = api_permalink(
        href=f"#{ids[0]}",
        title="Link to this definition",
    )
    link["classes"] = ["headerlink", API.LINK]
    return link


def _primary_signature_id(desc_node: addnodes.desc) -> str | None:
    """Return the first signature id for a ``desc`` node."""
    for child in desc_node.children:
        if isinstance(child, addnodes.desc_signature):
            ids: list[str] = [
                str(node_id) for node_id in t.cast(list[t.Any], child.get("ids", []))
            ]
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
    ['gp-sphinx-api-description', 'gp-sphinx-api-parameters']
    """
    content = next(
        (c for c in desc_node.children if isinstance(c, addnodes.desc_content)),
        None,
    )
    if content is None:
        return

    _append_class(content, API.CONTENT)
    if not content.children:
        return

    original = list(content.children)
    content.children = []

    current_kind: str | None = None
    current_section: api_component | None = None

    for child in original:
        if (
            isinstance(child, api_component)
            and str(child.get("name", "")) in _STRUCTURED_SECTION_NAMES
        ):
            if current_section is not None:
                content += current_section
                current_section = None
                current_kind = None
            content += child
            continue
        kind = _classify_child(child)
        if kind != current_kind:
            if current_section is not None:
                content += current_section
            current_section = build_api_component(
                _component_name_for_kind(kind),
                classes=(API.REGION, API.region_modifier(kind)),
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


def _deduplicate_return_type_fields(content: addnodes.desc_content) -> None:
    """Remove duplicate "Return type" fields, keeping the richest one.

    Remove duplicate "Return type" fields that can appear when multiple
    docstring processors each emit a ``:rtype:`` field.  ``sphinx_autodoc_typehints_gp``
    inserts its cross-referenced entry at priority 499 before the Sphinx
    built-in runs at 500, but the NumPy docstring parser may also produce a
    plain-text ``:rtype:`` that ``_enhance_existing_type_field`` upgrades in
    place.  This helper is a defensive safety net: it removes all but the
    first "Return type" field so no duplicate ever reaches the browser.

    Examples
    --------
    >>> from docutils import nodes
    >>> from sphinx import addnodes
    >>> content = addnodes.desc_content()
    >>> fl = nodes.field_list()
    >>> for label in ("Return type", "Returns", "Return type"):
    ...     f = nodes.field()
    ...     f += nodes.field_name("", label)
    ...     f += nodes.field_body("", nodes.paragraph("", label + " body"))
    ...     fl += f
    >>> content += fl
    >>> _deduplicate_return_type_fields(content)
    >>> rtype_fields = [
    ...     f for f in fl.children
    ...     if isinstance(f, nodes.field)
    ...     and f.children
    ...     and f.children[0].astext().lower() == "return type"
    ... ]
    >>> len(rtype_fields)
    1
    """
    for field_list in content.findall(nodes.field_list):
        seen_rtype = False
        for field in list(field_list.children):
            if not isinstance(field, nodes.field):
                continue
            name_node = field.children[0] if field.children else None
            if (
                isinstance(name_node, nodes.field_name)
                and name_node.astext().lower() == "return type"
            ):
                if seen_rtype:
                    field_list.remove(field)
                else:
                    seen_rtype = True


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
        return str(node.get("name", "")) == API.PARAMETERS
    if isinstance(node, api_region):
        return str(node.get("kind", "")) == "fields"
    return False


def _fold_large_field_regions(
    content: addnodes.desc_content,
    threshold: int,
) -> None:
    """Wrap large field-list regions in ``api_fold`` disclosure blocks."""
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
            fold = api_fold(
                kind="parameters",
                summary=f"Parameters ({entry_count})",
            )
            idx = section.children.index(field_list)
            section.remove(field_list)
            fold += field_list
            section.insert(idx, fold)


def _parameter_key(text: str) -> str:
    """Return a normalized parameter key for preview and type lookup.

    Examples
    --------
    >>> _parameter_key("host: str")
    'host'
    >>> _parameter_key("port: int = 5432")
    'port'
    """
    key = text.strip().rstrip(",")
    for separator in (":", "="):
        if separator in key:
            key = key.split(separator, 1)[0].rstrip()
    return key.strip()


def _count_signature_parameters(
    parameter_list: addnodes.desc_parameterlist,
) -> tuple[str, int]:
    """Return the first parameter text and total parameter count."""
    params = list(parameter_list.findall(addnodes.desc_parameter))
    first = _parameter_key(params[0].astext()) if params else ""
    return first, len(params)


def _signature_expanded_id(desc_sig: addnodes.desc_signature) -> str:
    """Return the stable DOM id for an expanded signature wrapper."""
    ids: list[str] = [
        str(node_id) for node_id in t.cast(list[t.Any], desc_sig.get("ids", []))
    ]
    base = ids[0] if ids else API.SIGNATURE
    return f"{base}--signature-expanded"


def _parameter_has_annotation(parameter: addnodes.desc_parameter) -> bool:
    """Return ``True`` when a parameter already contains a type annotation."""
    return any(
        isinstance(child, addnodes.desc_sig_punctuation) and ":" in child.astext()
        for child in parameter.children
    )


def _parameter_default_index(parameter: addnodes.desc_parameter) -> int | None:
    """Return the index of the default operator, if present."""
    for index, child in enumerate(parameter.children):
        if isinstance(child, addnodes.desc_sig_operator) and child.astext() == "=":
            return index
    return None


def _is_space_node(child: nodes.Node) -> bool:
    """Return ``True`` when a node renders as whitespace only."""
    return child.astext().isspace()


def _replace_parameter_children(
    parameter: addnodes.desc_parameter,
    children: list[nodes.Node],
) -> None:
    """Replace a parameter's direct children with *children*."""
    parameter.children = []
    for child in children:
        parameter += child


def _strip_parameter_annotation(parameter: addnodes.desc_parameter) -> None:
    """Remove only the parameter annotation while preserving defaults."""
    children = list(parameter.children)
    annotation_start = next(
        (
            index
            for index, child in enumerate(children)
            if isinstance(child, addnodes.desc_sig_punctuation)
            and ":" in child.astext()
        ),
        None,
    )
    if annotation_start is None:
        return

    default_index = _parameter_default_index(parameter)
    prefix = children[:annotation_start]
    while prefix and _is_space_node(prefix[-1]):
        prefix.pop()

    if default_index is None:
        _replace_parameter_children(parameter, prefix)
        return

    suffix = children[default_index:]
    while len(suffix) > 1 and _is_space_node(suffix[1]):
        suffix.pop(1)
    _replace_parameter_children(parameter, [*prefix, *suffix])


def _make_annotation_nodes(type_nodes: list[nodes.Node]) -> list[nodes.Node]:
    """Create signature annotation nodes from cloned *type_nodes*."""
    type_name = addnodes.desc_sig_name("", "")
    for child in type_nodes:
        type_name += child.deepcopy()
    return [
        addnodes.desc_sig_punctuation("", ":"),
        addnodes.desc_sig_space("", " "),
        type_name,
    ]


def _inject_parameter_annotation(
    parameter: addnodes.desc_parameter,
    type_nodes: list[nodes.Node],
) -> None:
    """Insert a type annotation before a parameter default, if needed."""
    if not type_nodes or _parameter_has_annotation(parameter):
        return

    key = _parameter_key(parameter.astext())
    if key in {"*", "/"}:
        return

    children = list(parameter.children)
    default_index = _parameter_default_index(parameter)
    insert_at = len(children) if default_index is None else default_index

    annotation_children = _make_annotation_nodes(type_nodes)
    if default_index is not None:
        annotation_children.append(addnodes.desc_sig_space("", " "))

    children[insert_at:insert_at] = annotation_children

    if default_index is not None:
        operator_index = insert_at + len(annotation_children)
        next_index = operator_index + 1
        if next_index < len(children) and not _is_space_node(children[next_index]):
            children.insert(next_index, addnodes.desc_sig_space("", " "))

    _replace_parameter_children(parameter, children)


def _iter_parameter_paragraphs(
    field_body: nodes.field_body,
) -> t.Iterator[nodes.paragraph]:
    """Yield parameter paragraphs from a Sphinx ``Parameters`` field body."""
    for child in field_body.children:
        if isinstance(child, nodes.bullet_list):
            for item in child.children:
                if not isinstance(item, nodes.list_item):
                    continue
                for grandchild in item.children:
                    if isinstance(grandchild, nodes.paragraph):
                        yield grandchild
        elif isinstance(child, nodes.paragraph):
            yield child


def _extract_type_nodes_from_paragraph(
    paragraph: nodes.paragraph,
) -> tuple[str, list[nodes.Node]] | None:
    """Extract a parameter name and its type nodes from a field-list paragraph."""
    if not paragraph.children:
        return None

    first = paragraph.children[0]
    if not isinstance(first, (nodes.strong, addnodes.literal_strong)):
        return None

    key = _parameter_key(first.astext())
    if not key:
        return None

    collected: list[nodes.Node] = []
    in_type = False

    for child in paragraph.children[1:]:
        text = child.astext()
        if not in_type:
            if "(" not in text:
                continue
            in_type = True
            after_open = text.split("(", 1)[1]
            if ")" in after_open:
                before_close = after_open.split(")", 1)[0]
                if before_close:
                    collected.append(nodes.Text(before_close))
                break
            if after_open:
                collected.append(nodes.Text(after_open))
            continue

        if ")" in text:
            before_close = text.split(")", 1)[0]
            if before_close:
                collected.append(nodes.Text(before_close))
            break
        collected.append(child.deepcopy())

    if not collected:
        return None
    return key, collected


def _extract_parameter_types(desc_node: addnodes.desc) -> dict[str, list[nodes.Node]]:
    """Collect parameter annotations from the entry's ``Parameters`` field list."""
    content = next(
        (
            child
            for child in desc_node.children
            if isinstance(child, addnodes.desc_content)
        ),
        None,
    )
    if content is None:
        return {}

    mapping: dict[str, list[nodes.Node]] = {}
    for section in content.children:
        if not _is_parameters_section(section):
            continue
        assert isinstance(section, nodes.Element)
        for child in section.children:
            if not isinstance(child, nodes.field_list):
                continue
            for field in child.children:
                if not isinstance(field, nodes.field) or len(field.children) < 2:
                    continue
                name = field.children[0]
                body = field.children[1]
                if not isinstance(name, nodes.field_name) or not isinstance(
                    body, nodes.field_body
                ):
                    continue
                if name.astext().strip().casefold() != "parameters":
                    continue
                for paragraph in _iter_parameter_paragraphs(body):
                    extracted = _extract_type_nodes_from_paragraph(paragraph)
                    if extracted is None:
                        continue
                    key, type_nodes = extracted
                    mapping[key] = type_nodes
    return mapping


def _prepare_folded_parameter_list(
    parameter_list: addnodes.desc_parameterlist,
    *,
    parameter_types: dict[str, list[nodes.Node]],
    show_annotations: bool,
) -> None:
    """Convert a parameter list to Sphinx's multiline signature rendering."""
    parameter_list["multi_line_parameter_list"] = True
    parameter_list["multi_line_trailing_comma"] = False

    for parameter in parameter_list.findall(addnodes.desc_parameter):
        key = _parameter_key(parameter.astext())
        if show_annotations:
            if _parameter_has_annotation(parameter):
                continue
            type_nodes = parameter_types.get(key)
            if type_nodes is not None:
                _inject_parameter_annotation(parameter, type_nodes)
            continue
        _strip_parameter_annotation(parameter)


def _extract_toolbar_content(
    toolbar: nodes.inline | None,
) -> tuple[list[nodes.Node], nodes.reference | None]:
    """Split toolbar content into badge-side children and source link."""
    badge_children: list[nodes.Node] = []
    source_ref: nodes.reference | None = None

    if toolbar is None:
        return badge_children, source_ref

    for child in list(toolbar.children):
        if source_ref is None and is_viewcode_ref(child):
            assert isinstance(child, nodes.reference)
            source_ref = child
            continue
        badge_children.append(child)

    return badge_children, source_ref


def _pop_slot_children(slot_node: api_slot) -> list[nodes.Node]:
    """Detach and return all children from *slot_node* in source order."""
    slot_children: list[nodes.Node] = []
    for child in list(slot_node.children):
        slot_node.remove(child)
        slot_children.append(child)
    return slot_children


def _extract_slot_content(
    desc_sig: addnodes.desc_signature,
) -> dict[str, list[nodes.Node]]:
    """Return detached slot payloads keyed by slot name."""
    slot_children: dict[str, list[nodes.Node]] = {}
    for child in list(desc_sig.children):
        if not isinstance(child, api_slot):
            continue
        desc_sig.remove(child)
        slot_name = str(child.get("slot", ""))
        if not slot_name:
            continue
        slot_children.setdefault(slot_name, []).extend(_pop_slot_children(child))
    return slot_children


def _rebuild_signature_layout(
    desc_node: addnodes.desc,
    desc_sig: addnodes.desc_signature,
    *,
    threshold: int,
    include_permalink: bool,
    show_annotations: bool,
) -> None:
    """Rebuild a signature into explicit API header subcomponents."""
    if desc_sig.get("is_multiline"):
        return

    slot_children = _extract_slot_content(desc_sig)
    original = list(desc_sig.children)
    desc_sig.children = []

    toolbar: nodes.inline | None = None
    row_children: list[nodes.Node] = []
    fallback_source_ref: nodes.reference | None = None

    for child in original:
        if isinstance(child, nodes.inline) and SAB.TOOLBAR in child.get("classes", []):
            toolbar = child
            continue
        if isinstance(child, nodes.reference) and "headerlink" in child.get(
            "classes", []
        ):
            continue
        if fallback_source_ref is None and is_viewcode_ref(child):
            assert isinstance(child, nodes.reference)
            fallback_source_ref = child
            continue
        row_children.append(child)

    fallback_badge_children, source_ref = _extract_toolbar_content(toolbar)
    badge_children = slot_children.get("badges", fallback_badge_children)
    source_children = slot_children.get("source-link", [])
    if not source_children and source_ref is not None:
        source_children = [source_ref]
    if not source_children and fallback_source_ref is not None:
        source_children = [fallback_source_ref]

    layout = build_api_component(API.LAYOUT)
    left = build_api_component(API.LAYOUT_LEFT)
    signature = build_api_component(API.SIGNATURE)
    right = build_api_component(API.LAYOUT_RIGHT, classes=(SAB.TOOLBAR,))
    parameter_types = _extract_parameter_types(desc_node)
    folded = False

    for child in row_children:
        if not folded and isinstance(child, addnodes.desc_parameterlist):
            first_param, param_count = _count_signature_parameters(child)
            if param_count >= threshold:
                panel_id = _signature_expanded_id(desc_sig)
                signature += api_sig_fold(
                    first_param=first_param,
                    param_count=param_count,
                    panel_id=panel_id,
                )
                _prepare_folded_parameter_list(
                    child,
                    parameter_types=parameter_types,
                    show_annotations=show_annotations,
                )
                expanded = build_api_component(
                    API.SIGNATURE_EXPANDED,
                    classes=(API.SIG_EXPANDED,),
                    html_attrs={
                        "aria-hidden": "true",
                        "data-expanded": "false",
                        "hidden": "hidden",
                        "id": panel_id,
                    },
                )
                expanded += child
                collapse = build_api_inline_component(
                    API.SIG_COLLAPSE,
                    tag="button",
                    html_attrs={
                        "aria-controls": panel_id,
                        "aria-expanded": "true",
                        "type": "button",
                    },
                )
                collapse += nodes.Text("[collapse]")
                expanded += collapse
                signature += expanded
                folded = True
                continue
        signature += child

    left += signature
    if include_permalink:
        permalink = _make_api_permalink(desc_sig)
        if permalink is not None:
            left += permalink

    if badge_children:
        badge_container = build_api_inline_component(API.BADGE_CONTAINER)
        for child in badge_children:
            badge_container += child
        right += badge_container

    if source_children:
        source_container = build_api_inline_component(API.SOURCE_LINK)
        for child in source_children:
            source_container += child
        right += source_container

    layout += left
    layout += right
    desc_sig += layout


def on_doctree_resolved(
    app: Sphinx,
    doctree: nodes.document,
    docname: str,
) -> None:
    """Restructure managed Sphinx object entries into stable API components.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application.
    doctree : nodes.document
        The resolved doctree.
    docname : str
        The document name.
    """
    if app.builder.format != "html":
        return
    api_layout_enabled = bool(app.config.api_layout_enabled)
    if not api_layout_enabled and next(doctree.findall(api_slot), None) is None:
        return

    threshold: int = app.config.api_collapsed_threshold
    fold_params: bool = app.config.api_fold_parameters
    show_annotations: bool = app.config.api_signature_show_annotations
    include_permalink = bool(
        app.config.html_permalinks and getattr(app.builder, "add_permalinks", False)
    )

    _nest_python_members(doctree)

    for desc_node in doctree.findall(addnodes.desc):
        profile = _desc_layout_profile(desc_node)
        if profile is None:
            continue

        _append_class(desc_node, API.CONTAINER)
        _append_class(desc_node, profile.class_name)
        _wrap_content_runs(desc_node)

        for child in desc_node.children:
            if isinstance(child, addnodes.desc_content):
                _deduplicate_return_type_fields(child)

        allow_signature_fold = (
            api_layout_enabled and fold_params and profile.allow_signature_fold
        )

        for child in desc_node.children:
            if not isinstance(child, addnodes.desc_signature):
                continue
            _append_class(child, API.HEADER)
            child["api_managed"] = not child.get("is_multiline", False)
            if child["api_managed"]:
                child["html_attrs"] = {"data-signature-expanded": "false"}
            _rebuild_signature_layout(
                desc_node,
                child,
                threshold=threshold if allow_signature_fold else 10**9,
                include_permalink=include_permalink,
                show_annotations=show_annotations,
            )

        if not allow_signature_fold:
            continue

        content = next(
            (c for c in desc_node.children if isinstance(c, addnodes.desc_content)),
            None,
        )
        if content is not None:
            _fold_large_field_regions(content, threshold)
