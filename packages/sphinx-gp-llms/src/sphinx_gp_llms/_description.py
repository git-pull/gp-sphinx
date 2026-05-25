"""First-paragraph extraction from Sphinx doctrees.

Provides a lightweight description extractor that walks a doctree and
returns the text of the first body paragraph, suitable for use in
``llms.txt`` link descriptions and ``docs.json`` page summaries.

Examples
--------
>>> from sphinx_gp_llms._description import get_first_paragraph
>>> callable(get_first_paragraph)
True
"""

from __future__ import annotations

import typing as t

from docutils import nodes

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

_SKIP_PARENTS = (
    nodes.Admonition,
    nodes.field_list,
    nodes.sidebar,
    nodes.topic,
    nodes.comment,
    nodes.footnote,
)


def _is_body_paragraph(node: nodes.paragraph) -> bool:
    """Return True when *node* is a direct section-child paragraph."""
    parent = node.parent
    while parent is not None:
        if isinstance(parent, _SKIP_PARENTS):
            return False
        if isinstance(parent, nodes.section):
            return True
        parent = parent.parent
    return True


def get_first_paragraph(
    app: Sphinx,
    docname: str,
    max_length: int = 200,
) -> str:
    """Extract the first body paragraph from a page's doctree.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.
    docname : str
        Document name (without extension).
    max_length : int
        Maximum characters to return.

    Returns
    -------
    str
        Flattened paragraph text, truncated with ``...`` when exceeding
        *max_length*.

    Examples
    --------
    >>> from sphinx_gp_llms._description import get_first_paragraph
    >>> callable(get_first_paragraph)
    True
    """
    doctree = app.env.get_doctree(docname)
    title_text = ""
    if docname in app.env.titles:
        title_text = app.env.titles[docname].astext()

    for node in doctree.findall(nodes.paragraph):
        if not _is_body_paragraph(node):
            continue
        text = node.astext().replace("\n", " ").strip()
        if not text or text == title_text:
            continue
        if len(text) > max_length:
            return text[: max_length - 3] + "..."
        return text
    return ""
