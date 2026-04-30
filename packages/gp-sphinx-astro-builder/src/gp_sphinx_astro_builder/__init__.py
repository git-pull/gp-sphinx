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
from gp_sphinx_astro_builder.content_config import render_content_config
from gp_sphinx_astro_builder.models import (
    AdmonitionNode,
    AdmonitionVariant,
    ApiLayoutComponent,
    ApiLayoutNode,
    BadgeNode,
    BadgeSize,
    BadgeStyle,
    BlockNode,
    BlockQuoteNode,
    BulletListNode,
    CliCommandComponent,
    CliCommandNode,
    CommentNode,
    DefinitionListItemNode,
    DefinitionListNode,
    Document,
    EmphasisNode,
    EnumeratedListNode,
    FootnoteKind,
    FootnoteNode,
    FootnoteReferenceNode,
    ImageNode,
    InlineNode,
    ListItemNode,
    LiteralBlockNode,
    LiteralNode,
    ParagraphNode,
    Parameter,
    ParameterKind,
    ReferenceNode,
    RubricNode,
    SectionNode,
    StrongNode,
    Symbol,
    SymbolKind,
    SymbolRefNode,
    SymbolSource,
    TableCellNode,
    TableNode,
    TableRowNode,
    TextNode,
    TransitionNode,
    XrefEntry,
)
from gp_sphinx_astro_builder.schemas import (
    export_doctree_schema,
    export_symbol_schema,
    export_xref_index_schema,
)
from gp_sphinx_astro_builder.translator import DocTreeJSONTranslator

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = [
    "AdmonitionNode",
    "AdmonitionVariant",
    "ApiLayoutComponent",
    "ApiLayoutNode",
    "AstroBuilder",
    "BadgeNode",
    "BadgeSize",
    "BadgeStyle",
    "BlockNode",
    "BlockQuoteNode",
    "BulletListNode",
    "CliCommandComponent",
    "CliCommandNode",
    "CommentNode",
    "DefinitionListItemNode",
    "DefinitionListNode",
    "DocTreeJSONTranslator",
    "Document",
    "EmphasisNode",
    "EnumeratedListNode",
    "FootnoteKind",
    "FootnoteNode",
    "FootnoteReferenceNode",
    "ImageNode",
    "InlineNode",
    "ListItemNode",
    "LiteralBlockNode",
    "LiteralNode",
    "ParagraphNode",
    "Parameter",
    "ParameterKind",
    "ReferenceNode",
    "RubricNode",
    "SectionNode",
    "StrongNode",
    "Symbol",
    "SymbolKind",
    "SymbolRefNode",
    "SymbolSource",
    "TableCellNode",
    "TableNode",
    "TableRowNode",
    "TextNode",
    "TransitionNode",
    "XrefEntry",
    "export_doctree_schema",
    "export_symbol_schema",
    "export_xref_index_schema",
    "render_content_config",
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
    # Source-attribution config values — used by the translator's
    # ``_resolve_source`` to populate ``Symbol.source`` with deep
    # blob links to GitHub. Both default to ``""``/``None`` so the
    # builder gracefully degrades to ``Symbol.source = null`` when
    # the host project doesn't opt in.
    #
    # ``source_repository`` is the gp-sphinx convention (already
    # surfaced by ``merge_sphinx_config``); registering it here
    # promotes the conf.py value from a raw module variable into
    # ``app.config.source_repository`` for ``getattr`` access.
    app.add_config_value("source_repository", "", "env", str)
    app.add_config_value("astro_source_root", None, "env", (str, type(None)))
    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
