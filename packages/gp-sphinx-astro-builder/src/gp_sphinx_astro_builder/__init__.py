"""Sphinx builder that emits typed JSON for Astro static sites.

Examples
--------
>>> from gp_sphinx_astro_builder.models import TextNode
>>> TextNode(type="text", value="hi").model_dump()
{'type': 'text', 'value': 'hi'}
"""

from __future__ import annotations

import logging

from gp_sphinx_astro_builder.models import (
    BlockNode,
    Document,
    EmphasisNode,
    InlineNode,
    ParagraphNode,
    SectionNode,
    TextNode,
)
from gp_sphinx_astro_builder.translator import DocTreeJSONTranslator

__all__ = [
    "BlockNode",
    "DocTreeJSONTranslator",
    "Document",
    "EmphasisNode",
    "InlineNode",
    "ParagraphNode",
    "SectionNode",
    "TextNode",
]

logging.getLogger(__name__).addHandler(logging.NullHandler())

_EXTENSION_VERSION = "0.0.1a12"
