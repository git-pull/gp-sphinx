"""Pydantic models for the doctree-as-typed-JSON wire format.

Each docutils node type the builder emits has a matching Pydantic model. The
``type`` discriminator lets every node validate as part of a discriminated
union without ambiguity, and lets the TypeScript side dispatch on the same
field at render time.
"""

from __future__ import annotations

import typing as t

from pydantic import BaseModel


class TextNode(BaseModel):
    """A leaf node containing literal text.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.models import TextNode
    >>> node = TextNode(type="text", value="hello")
    >>> node.model_dump()
    {'type': 'text', 'value': 'hello'}
    """

    type: t.Literal["text"]
    value: str
