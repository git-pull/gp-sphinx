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

_MANAGED_DOCUTILS_OBJTYPES: tuple[str, ...] = (
    "transform",
    "reader",
    "parser",
    "writer",
    "node",
    "translator",
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
    **{
        ("docutils", objtype): DescLayoutProfile(
            domain="docutils",
            objtype=objtype,
            slug=f"docutils-{objtype}",
        )
        for objtype in _MANAGED_DOCUTILS_OBJTYPES
    },
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


_LAYOUT_VARIANTS: t.Final[tuple[str, ...]] = ("desktop", "mobile")
"""Stable variant tags emitted side-by-side in every managed header.

CSS in ``layout.css`` toggles visibility between the two via container
queries on ``dl.gp-sphinx-api-container``; only one variant is rendered at
a time, but both ship in the DOM so the cascade can pick the right one
per containing column without JS measurement.
"""


def _signature_expanded_id(
    desc_sig: addnodes.desc_signature, variant: str | None = None
) -> str:
    """Return the stable DOM id for an expanded signature wrapper.

    When ``variant`` is provided it is appended as a suffix so each layout
    variant (desktop / mobile) ships with a distinct, addressable panel id.
    """
    ids: list[str] = [
        str(node_id) for node_id in t.cast(list[t.Any], desc_sig.get("ids", []))
    ]
    base = ids[0] if ids else API.SIGNATURE
    suffix = "--signature-expanded"
    if variant is not None:
        suffix = f"{suffix}-{variant}"
    return f"{base}{suffix}"


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


@dataclasses.dataclass(frozen=True, slots=True)
class _HeaderInputs:
    """Parsed material for one or more header layout variants.

    ``signature_row_children`` is the list of inline nodes that belong in
    the signature column (operating from the original ``desc_signature``
    children minus toolbar/source/headerlink siblings). ``badge_children``
    and ``source_children`` populate the toolbar; ``param_count`` /
    ``first_param`` are pre-computed so metadata callers don't re-walk
    the parameter list.
    """

    signature_row_children: tuple[nodes.Node, ...]
    badge_children: tuple[nodes.Node, ...]
    source_children: tuple[nodes.Node, ...]
    parameter_types: dict[str, list[nodes.Node]]
    first_param: str
    param_count: int
    has_parameter_list: bool


def _parse_signature_inputs(
    desc_node: addnodes.desc,
    desc_sig: addnodes.desc_signature,
) -> _HeaderInputs:
    """Detach the signature's children and partition them by destination.

    Slots, the legacy badge toolbar, viewcode source link, headerlink, and
    everything else are split apart so each layout variant can rebuild a
    fresh subtree from independently deepcopied parts.
    """
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

    first_param = ""
    param_count = 0
    has_parameter_list = False
    for child in row_children:
        if isinstance(child, addnodes.desc_parameterlist):
            has_parameter_list = True
            first_param, param_count = _count_signature_parameters(child)
            break

    return _HeaderInputs(
        signature_row_children=tuple(row_children),
        badge_children=tuple(badge_children),
        source_children=tuple(source_children),
        parameter_types=_extract_parameter_types(desc_node),
        first_param=first_param,
        param_count=param_count,
        has_parameter_list=has_parameter_list,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class _HeaderMetadata:
    """Builder-driven metadata about a managed header.

    Both the boolean ``classes`` (CSS modifier list) and the ``data_attrs``
    (data-* attributes on the rendered ``<dt>``) describe styling-relevant
    facts CSS can't compute on its own — number of badges, presence of a
    source link, whether the signature folds, the Sphinx domain/objtype.
    """

    classes: tuple[str, ...]
    data_attrs: dict[str, str]


def _compute_header_metadata(
    desc_node: addnodes.desc,
    inputs: _HeaderInputs,
    *,
    threshold: int,
) -> _HeaderMetadata:
    """Derive class modifiers and data-* attributes for the managed header."""
    domain = str(desc_node.get("domain", "") or "")
    objtype = str(desc_node.get("objtype", "") or "")
    badge_count = len(inputs.badge_children)
    has_source = bool(inputs.source_children)
    has_badges = badge_count > 0
    has_fold = inputs.has_parameter_list and inputs.param_count >= threshold

    data_attrs: dict[str, str] = {"data-signature-expanded": "false"}
    if domain:
        data_attrs["data-domain"] = domain
    if objtype:
        data_attrs["data-objtype"] = objtype
    data_attrs["data-has-source"] = "true" if has_source else "false"
    data_attrs["data-has-badges"] = "true" if has_badges else "false"
    data_attrs["data-badge-count"] = str(badge_count)
    data_attrs["data-has-fold"] = "true" if has_fold else "false"

    classes: list[str] = []
    if has_source:
        classes.append(API.HEADER_HAS_SOURCE)
    if has_badges:
        classes.append(API.HEADER_HAS_BADGES)
    if has_fold:
        classes.append(API.HEADER_HAS_FOLD)

    return _HeaderMetadata(classes=tuple(classes), data_attrs=data_attrs)


def _build_signature_column(
    desc_sig: addnodes.desc_signature,
    inputs: _HeaderInputs,
    *,
    variant: str,
    threshold: int,
    show_annotations: bool,
    include_permalink: bool,
) -> tuple[api_component, api_permalink | None]:
    """Build a fresh signature column (signature + permalink) for one variant.

    Every node is deepcopied from ``inputs`` so each variant owns an
    independent subtree — docutils requires single parentage and the
    expanded panel id needs to be variant-specific.
    """
    signature = build_api_component(API.SIGNATURE)
    folded = False

    for child in inputs.signature_row_children:
        cloned = child.deepcopy() if isinstance(child, nodes.Node) else child
        if (
            not folded
            and isinstance(cloned, addnodes.desc_parameterlist)
            and inputs.has_parameter_list
            and inputs.param_count >= threshold
        ):
            panel_id = _signature_expanded_id(desc_sig, variant=variant)
            signature += api_sig_fold(
                first_param=inputs.first_param,
                param_count=inputs.param_count,
                panel_id=panel_id,
            )
            _prepare_folded_parameter_list(
                cloned,
                parameter_types=inputs.parameter_types,
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
            expanded += cloned
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
        signature += cloned

    permalink = _make_api_permalink(desc_sig) if include_permalink else None
    return signature, permalink


def _clone_node(node: nodes.Node) -> nodes.Node:
    """Return an independent copy of *node* via docutils' own ``deepcopy``.

    Stdlib ``copy.deepcopy`` is unsafe for docutils nodes: ``Node`` does not
    override ``__deepcopy__``, so the default machinery follows ``.parent``
    upward and clones every ancestor.  Docutils' ``Element.deepcopy`` /
    ``Text.deepcopy`` walk only descendants, which is what we want when
    duplicating header content for the desktop and mobile variants.
    """
    if isinstance(node, nodes.Node):
        return node.deepcopy()
    return node


def _build_toolbar_column(
    inputs: _HeaderInputs,
    *,
    classes: tuple[str, ...],
    name: str,
) -> api_component:
    """Build a fresh toolbar column (badges + source) for one variant.

    Each toolbar gets a docutils-native deep copy of the badge / source
    nodes so the two layout variants are independent subtrees.
    """
    column = build_api_component(name, classes=(SAB.TOOLBAR, *classes))
    if inputs.badge_children:
        badge_container = build_api_inline_component(API.BADGE_CONTAINER)
        for child in inputs.badge_children:
            badge_container += _clone_node(child)
        column += badge_container
    if inputs.source_children:
        source_container = build_api_inline_component(API.SOURCE_LINK)
        for child in inputs.source_children:
            source_container += _clone_node(child)
        column += source_container
    return column


def _build_layout_variant(
    desc_sig: addnodes.desc_signature,
    inputs: _HeaderInputs,
    *,
    variant: str,
    threshold: int,
    show_annotations: bool,
    include_permalink: bool,
) -> api_component:
    """Build a complete ``gp-sphinx-api-layout--<variant>`` subtree.

    Desktop variant: ``[ left(signature, permalink), right(toolbar) ]``.
    Mobile variant:  ``[ top(toolbar), bottom(signature, permalink) ]``.

    The horizontal/vertical naming reflects each variant's intended layout
    axis (desktop = inline row, mobile = block stack); CSS uses container
    queries on ``dl.gp-sphinx-api-container`` to toggle which one is
    visible.
    """
    layout = build_api_component(API.LAYOUT, classes=(API.layout_variant(variant),))
    signature, permalink = _build_signature_column(
        desc_sig,
        inputs,
        variant=variant,
        threshold=threshold,
        show_annotations=show_annotations,
        include_permalink=include_permalink,
    )

    if variant == "desktop":
        left = build_api_component(API.LAYOUT_LEFT)
        left += signature
        if permalink is not None:
            left += permalink
        right = _build_toolbar_column(
            inputs,
            classes=(),
            name=API.LAYOUT_RIGHT,
        )
        layout += left
        layout += right
        return layout

    # variant == "mobile" — toolbar on top, signature on the bottom.  This
    # avoids the desktop's `order: -1` flex hack: each variant owns the
    # natural DOM order it needs, and CSS picks one to display per
    # container width.
    top = _build_toolbar_column(
        inputs,
        classes=(),
        name=API.LAYOUT_TOP,
    )
    bottom = build_api_component(API.LAYOUT_BOTTOM)
    bottom += signature
    if permalink is not None:
        bottom += permalink
    layout += top
    layout += bottom
    return layout


def _rebuild_signature_layout(
    desc_node: addnodes.desc,
    desc_sig: addnodes.desc_signature,
    *,
    threshold: int,
    include_permalink: bool,
    show_annotations: bool,
) -> None:
    """Rebuild a signature into desktop + mobile API header variants.

    Each variant is a fully independent subtree (deepcopied content) so
    docutils' single-parent invariant is preserved and CSS can hide one
    variant entirely without leaving stale shared state.  The desc
    signature also receives builder-driven ``data-*`` metadata and
    boolean modifier classes so theme CSS can branch on facts that the
    cascade alone cannot derive (badge count, source-link presence,
    fold availability).
    """
    if desc_sig.get("is_multiline"):
        return

    inputs = _parse_signature_inputs(desc_node, desc_sig)
    metadata = _compute_header_metadata(desc_node, inputs, threshold=threshold)

    existing_attrs = t.cast(dict[str, str], desc_sig.get("html_attrs", {}) or {})
    merged_attrs: dict[str, str] = {**existing_attrs, **metadata.data_attrs}
    desc_sig["html_attrs"] = merged_attrs
    for class_name in metadata.classes:
        _append_class(desc_sig, class_name)

    for variant in _LAYOUT_VARIANTS:
        desc_sig += _build_layout_variant(
            desc_sig,
            inputs,
            variant=variant,
            threshold=threshold,
            show_annotations=show_annotations,
            include_permalink=include_permalink,
        )


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
