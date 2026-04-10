"""Unconventional typehints extension for gp-sphinx."""

from __future__ import annotations

from sphinx_typehints_gp.extension import setup
from sphinx_typehints_gp.rendering import (
    build_annotation_paragraph,
    build_resolved_annotation_paragraph,
    normalize_annotation_text,
    normalize_type_collection_text,
    render_annotation_nodes,
)

__all__ = [
    "build_annotation_paragraph",
    "build_resolved_annotation_paragraph",
    "normalize_annotation_text",
    "normalize_type_collection_text",
    "render_annotation_nodes",
    "setup",
]
