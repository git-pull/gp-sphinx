"""Doctree-resolved transforms, missing-reference handler, and HTML visitors."""

from __future__ import annotations

import typing as t

from docutils import nodes
from sphinx import addnodes
from sphinx.util import logging as sphinx_logging
from sphinx.util.nodes import make_refnode

from sphinx_autodoc_pytest_fixtures._badges import _build_badge_group_node
from sphinx_autodoc_pytest_fixtures._constants import _FIELD_LABELS
from sphinx_autodoc_pytest_fixtures._index import _resolve_fixture_index
from sphinx_autodoc_pytest_fixtures._models import autofixture_index_node
from sphinx_autodoc_pytest_fixtures._store import FixtureStoreDict, _get_spf_store
from sphinx_ux_autodoc_layout import (
    API,
    build_api_table_section,
    inject_signature_slots,
)

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.domains.python import PythonDomain

    pass

logger = sphinx_logging.getLogger(__name__)

_PARAMETER_FIELD_LABELS = frozenset(
    {"parameter", "parameters", "return", "returns", "yield", "yields", "raises"}
)


def _on_missing_reference(
    app: t.Any,
    env: t.Any,
    node: t.Any,
    contnode: t.Any,
) -> t.Any | None:
    r"""Resolve ``:func:\`name\``` cross-references to ``py:fixture`` entries.

    Parameters
    ----------
    app : Any
        The Sphinx application.
    env : Any
        The Sphinx build environment.
    node : Any
        The pending cross-reference node.
    contnode : Any
        The content node to wrap.

    Returns
    -------
    Any or None
        A resolved reference node, or ``None`` to let Sphinx continue.

    Notes
    -----
    Handles MyST ``{func}\\`name\\``` references in ``usage.md`` that predate
    the ``py:fixture`` registration. The ``ObjType`` fallback roles cover most
    cases; this handler covers the ``any`` and implicit-domain paths.
    """
    if node.get("refdomain") != "py":
        return None

    reftype = node.get("reftype")
    target = node.get("reftarget", "")
    py_domain = env.domains.python_domain

    # Short-name :fixture: lookup via public_to_canon.
    if reftype == "fixture":
        store = _get_spf_store(env)
        canon = store["public_to_canon"].get(target)
        if canon:  # None means ambiguous — let Sphinx emit standard warning
            return py_domain.resolve_xref(
                env,
                node.get("refdoc", ""),
                app.builder,
                "fixture",
                canon,
                node,
                contnode,
            )
        return None

    # Existing func/obj/any fallback for legacy :func: references.
    if reftype not in {"func", "obj", "any"}:
        return None

    matches = py_domain.find_obj(
        env,
        node.get("py:module", ""),
        node.get("py:class", ""),
        target,
        "fixture",
        1,
    )
    if not matches:
        return None

    match_name, _obj_entry = matches[0]
    return py_domain.resolve_xref(
        env,
        node.get("refdoc", ""),
        app.builder,
        "fixture",
        match_name,
        node,
        contnode,
    )


def _inject_badges_and_reorder(sig_node: addnodes.desc_signature) -> None:
    """Inject scope/kind/fixture badges into shared layout slots.

    Guarded by the ``spf_badges_injected`` flag \u2014 safe to call multiple times.
    """
    scope = sig_node.get("spf_scope", "function")
    kind = sig_node.get("spf_kind", "resource")
    autouse = sig_node.get("spf_autouse", False)
    deprecated = sig_node.get("spf_deprecated", False)

    badge_group = _build_badge_group_node(scope, kind, autouse, deprecated=deprecated)
    inject_signature_slots(
        sig_node,
        marker_attr="spf_badges_injected",
        badge_node=badge_group,
    )


def _strip_rtype_fields(desc_node: addnodes.desc) -> None:
    """Remove redundant "Rtype" fields from fixture descriptions.

    ``sphinx_autodoc_typehints_gp`` emits these for all autodoc objects; for
    fixtures the return type is already in the signature line (``→ Type``).
    """
    for content_child in desc_node.findall(addnodes.desc_content):
        for fl in list(content_child.findall(nodes.field_list)):
            for field in list(fl.children):
                if not isinstance(field, nodes.field):
                    continue
                field_name = field.children[0] if field.children else None
                if (
                    isinstance(field_name, nodes.field_name)
                    and field_name.astext().lower() == "rtype"
                ):
                    fl.remove(field)
            if not fl.children:
                content_child.remove(fl)


def _wrap_fixture_field_lists(desc_node: addnodes.desc) -> None:
    """Wrap top-level fixture field lists in shared body sections."""
    for content_child in desc_node.findall(addnodes.desc_content):
        for field_list in list(content_child.children):
            if not isinstance(field_list, nodes.field_list):
                continue
            labels = {
                field_name.astext().strip().lower()
                for field_name in field_list.findall(nodes.field_name)
            }
            section_name = (
                API.PARAMETERS if labels & _PARAMETER_FIELD_LABELS else API.FACTS
            )
            insert_idx = content_child.children.index(field_list)
            content_child.remove(field_list)
            content_child.insert(
                insert_idx,
                build_api_table_section(section_name, field_list),
            )


def _inject_metadata_fields(
    desc_node: addnodes.desc,
    store: FixtureStoreDict,
    py_domain: PythonDomain,
    app: Sphinx,
    docname: str,
) -> None:
    """Inject "Used by" and "Parametrized" fields into fixture descriptions.

    Uses :func:`make_refnode` for "Used by" links because ``pending_xref``
    nodes added during ``doctree-resolved`` are too late for normal reference
    resolution.

    Guarded by ``spf_metadata_injected`` \u2014 safe to call multiple times.
    """
    if desc_node.get("spf_metadata_injected"):
        return
    desc_node["spf_metadata_injected"] = True

    first_sig = next(desc_node.findall(addnodes.desc_signature), None)
    if first_sig is None:
        return
    canon = first_sig.get("spf_canonical_name", "")
    if not canon:
        return

    meta = store["fixtures"].get(canon)
    content_node = None
    for child in desc_node.children:
        if isinstance(child, addnodes.desc_content):
            content_node = child
            break
    if content_node is None:
        return

    extra_fields = nodes.field_list()

    # "Used by" field \u2014 resolved links via make_refnode
    consumers = store.get("reverse_deps", {}).get(canon, [])
    if consumers:
        body_para = nodes.paragraph()
        for i, consumer_canon in enumerate(sorted(consumers)):
            short = consumer_canon.rsplit(".", 1)[-1]
            obj_entry = py_domain.objects.get(consumer_canon)
            if obj_entry is not None:
                ref_node: nodes.Node = make_refnode(
                    app.builder,
                    docname,
                    obj_entry.docname,
                    obj_entry.node_id,
                    nodes.literal(short, short),
                )
            else:
                ref_node = nodes.literal(short, short)
            body_para += ref_node
            if i < len(consumers) - 1:
                body_para += nodes.Text(", ")
        extra_fields += nodes.field(
            "",
            nodes.field_name("", _FIELD_LABELS["used_by"]),
            nodes.field_body("", body_para),
        )

    # "Parametrized" field — render from FixtureMeta.param_reprs tuple
    if meta and meta.param_reprs:
        if len(meta.param_reprs) <= 3:
            # Inline for short lists
            body_node: nodes.Element = nodes.paragraph()
            for i, param_repr in enumerate(meta.param_reprs):
                body_node += nodes.literal(param_repr, param_repr)
                if i < len(meta.param_reprs) - 1:
                    body_node += nodes.Text(", ")
        else:
            # Enumerated list for longer param lists
            body_node = nodes.enumerated_list(enumtype="arabic")
            for param_repr in meta.param_reprs:
                item = nodes.list_item()
                item += nodes.paragraph("", "", nodes.literal(param_repr, param_repr))
                body_node += item
        extra_fields += nodes.field(
            "",
            nodes.field_name("", _FIELD_LABELS["parametrized"]),
            nodes.field_body("", body_node),
        )

    if extra_fields.children:
        existing_list = next(content_node.findall(nodes.field_list), None)
        if existing_list is not None:
            for child in list(extra_fields.children):
                existing_list += child
        else:
            content_node += extra_fields


def _on_doctree_resolved(
    app: Sphinx,
    doctree: nodes.document,
    docname: str,
) -> None:
    """Inject badges and metadata fields into ``py:fixture`` descriptions.

    Orchestrates three focused helpers in the correct order:
    badges first, rtype stripping second, metadata injection third.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application instance.
    doctree : nodes.document
        The resolved document tree.
    docname : str
        The name of the document being resolved.
    """
    store = _get_spf_store(app.env)
    py_domain = app.env.domains.python_domain

    for desc_node in doctree.findall(addnodes.desc):
        if desc_node.get("objtype") != "fixture":
            continue

        for sig_node in desc_node.findall(addnodes.desc_signature):
            _inject_badges_and_reorder(sig_node)
        _strip_rtype_fields(desc_node)
        _inject_metadata_fields(desc_node, store, py_domain, app, docname)
        _wrap_fixture_field_lists(desc_node)

    # Resolve autofixture-index placeholders
    for idx_node in list(doctree.findall(autofixture_index_node)):
        _resolve_fixture_index(idx_node, store, py_domain, app, docname)
