"""Sphinx builder that emits typed JSON for Astro static sites.

Examples
--------
>>> from gp_sphinx_astro_builder.models import TextNode
>>> TextNode(type="text", value="hi").model_dump()
{'type': 'text', 'value': 'hi'}

>>> from gp_sphinx_astro_builder import setup
>>> callable(setup)
True
"""

from __future__ import annotations

import logging
import typing as t

from gp_sphinx_astro_builder.builder import AstroBuilder
from gp_sphinx_astro_builder.models import (
    BlockNode,
    BlockQuoteNode,
    CommentNode,
    Document,
    EmphasisNode,
    ImageNode,
    InlineNode,
    LiteralBlockNode,
    LiteralNode,
    ParagraphNode,
    ReferenceNode,
    SectionNode,
    StrongNode,
    TextNode,
    TransitionNode,
)
from gp_sphinx_astro_builder.translator import DocTreeJSONTranslator

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = [
    "AstroBuilder",
    "BlockNode",
    "BlockQuoteNode",
    "CommentNode",
    "DocTreeJSONTranslator",
    "Document",
    "EmphasisNode",
    "ImageNode",
    "InlineNode",
    "LiteralBlockNode",
    "LiteralNode",
    "ParagraphNode",
    "ReferenceNode",
    "SectionNode",
    "StrongNode",
    "TextNode",
    "TransitionNode",
    "setup",
]

logging.getLogger(__name__).addHandler(logging.NullHandler())

_EXTENSION_VERSION = "0.0.1a12"


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register :class:`AstroBuilder` with the Sphinx application.

    Parameters
    ----------
    app
        Sphinx application.

    Returns
    -------
    dict[str, Any]
        Extension metadata.

    Examples
    --------
    >>> from gp_sphinx_astro_builder import setup
    >>> callable(setup)
    True
    """
    app.add_builder(AstroBuilder)
    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
