"""Doctree-resolved transforms and HTML visitors for sphinx_autodoc_api_style.

Injects badge groups into Python domain ``desc`` nodes and provides a
custom ``abbreviation`` HTML visitor that emits ``tabindex`` for
keyboard-accessible tooltips.
"""

from __future__ import annotations

import typing as t

from docutils import nodes
from sphinx import addnodes
from sphinx.util import logging as sphinx_logging

from sphinx_autodoc_api_style._badges import build_badge_group
from sphinx_ux_autodoc_layout import inject_signature_slots

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = sphinx_logging.getLogger(__name__)

_HANDLED_OBJTYPES: frozenset[str] = frozenset(
    {
        "function",
        "class",
        "method",
        "classmethod",
        "staticmethod",
        "property",
        "attribute",
        "data",
        "exception",
        "type",
    },
)

_SKIP_OBJTYPES: frozenset[str] = frozenset(
    {
        "fixture",
        "module",
    },
)

_KEYWORD_TO_MOD: dict[str, str] = {
    "async": "async",
    "classmethod": "classmethod",
    "static": "staticmethod",
    "abstract": "abstract",
    "abstractmethod": "abstract",
    "final": "final",
}


def _detect_modifiers(sig_node: addnodes.desc_signature) -> frozenset[str]:
    """Detect modifier keywords from a signature node's annotations.

    Walks ``desc_annotation`` children looking for ``desc_sig_keyword``
    nodes whose text maps to a known modifier.

    Parameters
    ----------
    sig_node : addnodes.desc_signature
        The signature node to inspect.

    Returns
    -------
    frozenset[str]
        Set of detected modifier names.

    Examples
    --------
    >>> from sphinx import addnodes
    >>> sig = addnodes.desc_signature()
    >>> ann = addnodes.desc_annotation()
    >>> ann += addnodes.desc_sig_keyword("", "async")
    >>> sig += ann
    >>> sorted(_detect_modifiers(sig))
    ['async']
    """
    mods: set[str] = set()
    for ann in sig_node.findall(addnodes.desc_annotation):
        for kw in ann.findall(addnodes.desc_sig_keyword):
            text = kw.astext().strip()
            if text in _KEYWORD_TO_MOD:
                mods.add(_KEYWORD_TO_MOD[text])
    return frozenset(mods)


def _detect_deprecated(desc_node: addnodes.desc) -> bool:
    """Check whether a desc node's own content has a deprecation notice.

    Looks for ``versionmodified`` nodes with ``type='deprecated'`` in
    direct ``desc_content`` children, excluding content nested inside
    child ``desc`` nodes (so a class is not marked deprecated just
    because one of its methods is).

    Parameters
    ----------
    desc_node : addnodes.desc
        The description node to inspect.

    Returns
    -------
    bool
        ``True`` if a deprecation notice is found.

    Examples
    --------
    >>> from sphinx import addnodes
    >>> desc = addnodes.desc()
    >>> _detect_deprecated(desc)
    False
    """
    for child in desc_node.children:
        if not isinstance(child, addnodes.desc_content):
            continue
        for node in child.findall(addnodes.versionmodified):
            if node.get("type") != "deprecated":
                continue
            parent = node.parent
            inside_nested = False
            while parent is not None and parent is not child:
                if isinstance(parent, addnodes.desc):
                    inside_nested = True
                    break
                parent = parent.parent
            if not inside_nested:
                return True
    return False


def _inject_badges(sig_node: addnodes.desc_signature, objtype: str) -> None:
    """Inject structured layout slots containing badges and source links.

    Guarded by ``sab_badges_injected`` flag.

    Parameters
    ----------
    sig_node : addnodes.desc_signature
        The signature node to modify.
    objtype : str
        Python domain object type.

    Examples
    --------
    >>> from sphinx import addnodes
    >>> sig = addnodes.desc_signature()
    >>> sig += addnodes.desc_name("", "my_func")
    >>> _inject_badges(sig, "function")
    >>> sig.get("sab_badges_injected")
    True
    """
    mods = _detect_modifiers(sig_node)
    parent = sig_node.parent
    if isinstance(parent, addnodes.desc) and _detect_deprecated(parent):
        mods = mods | {"deprecated"}

    badge_group = build_badge_group(objtype, modifiers=mods)
    inject_signature_slots(
        sig_node,
        marker_attr="sab_badges_injected",
        badge_node=badge_group,
    )


def _prune_empty_desc_content(desc_node: addnodes.desc) -> None:
    """Remove empty desc_content nodes from a desc tree.

    Sphinx always appends a desc_content child even when the object has
    no docstring. An empty <dd></dd> wastes vertical space and creates
    layout noise. Remove it so the CSS card only shows the signature row.

    Parameters
    ----------
    desc_node : addnodes.desc
        The description node to inspect.

    Examples
    --------
    >>> from sphinx import addnodes
    >>> desc = addnodes.desc()
    >>> desc += addnodes.desc_content()          # empty
    >>> _prune_empty_desc_content(desc)
    >>> any(isinstance(c, addnodes.desc_content) for c in desc.children)
    False
    """
    for child in list(desc_node.children):
        if isinstance(child, addnodes.desc_content) and not child.children:
            desc_node.remove(child)


def on_doctree_resolved(
    app: Sphinx,
    doctree: nodes.document,
    docname: str,
) -> None:
    """Inject badges into Python domain description nodes.

    Connected to the ``doctree-resolved`` event. Walks all ``desc``
    nodes, filters to Python domain entries, and injects badge groups
    for functions, classes, methods, properties, attributes, etc.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application instance.
    doctree : nodes.document
        The resolved document tree.
    docname : str
        The name of the document being resolved.

    Examples
    --------
    >>> from unittest.mock import MagicMock
    >>> app = MagicMock()
    >>> from docutils import nodes
    >>> doc = nodes.document(None, None)
    >>> on_doctree_resolved(app, doc, "index")
    """
    for desc_node in doctree.findall(addnodes.desc):
        domain = desc_node.get("domain")
        objtype = desc_node.get("objtype", "")

        if domain != "py":
            continue
        if objtype in _SKIP_OBJTYPES:
            continue
        if objtype not in _HANDLED_OBJTYPES:
            continue

        for child in desc_node.children:
            if isinstance(child, addnodes.desc_signature):
                _inject_badges(child, objtype)
        _prune_empty_desc_content(desc_node)
