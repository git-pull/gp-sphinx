"""Toctree section extraction for llms.txt grouping.

Walks the root document's doctree to find ``toctree`` directives and
their ``:caption:`` options, producing a flat list of sections suitable
for the H2-delimited structure of ``llms.txt``.

Examples
--------
>>> from sphinx_gp_llms._toctree import ToctreeSection
>>> s = ToctreeSection(caption="Guide", docnames=["quickstart"])
>>> s.caption
'Guide'
"""

from __future__ import annotations

import typing as t

from sphinx import addnodes

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx


class ToctreeSection(t.NamedTuple):
    """One section of pages grouped by toctree caption.

    Examples
    --------
    >>> ToctreeSection(caption="API", docnames=["api/index"])
    ToctreeSection(caption='API', docnames=['api/index'])
    """

    caption: str | None
    docnames: list[str]


def extract_toctree_sections(app: Sphinx) -> list[ToctreeSection]:
    """Walk the root document's toctree nodes and group pages by caption.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance (must have a built environment).

    Returns
    -------
    list[ToctreeSection]
        Sections in document order.  Pages not referenced by any
        toctree in the root document get a ``caption=None`` fallback
        section at the end.

    Examples
    --------
    >>> from sphinx_gp_llms._toctree import extract_toctree_sections
    >>> callable(extract_toctree_sections)
    True
    """
    root_doc = app.config.root_doc
    doctree = app.env.get_doctree(root_doc)

    sections: list[ToctreeSection] = []
    assigned: set[str] = set()

    for toctree_node in doctree.findall(addnodes.toctree):
        caption = toctree_node.get("caption")
        docnames: list[str] = []
        for _title, docname in toctree_node["entries"]:
            if docname and docname in app.env.found_docs and docname not in assigned:
                docnames.append(docname)
                assigned.add(docname)
        if docnames:
            sections.append(ToctreeSection(caption=caption, docnames=docnames))

    remaining = sorted(app.env.found_docs - assigned - {root_doc})
    if remaining:
        sections.append(ToctreeSection(caption=None, docnames=remaining))

    return sections
