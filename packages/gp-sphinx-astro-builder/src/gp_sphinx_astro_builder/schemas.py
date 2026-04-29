"""JSON Schema export for the doctree wire format.

Pydantic owns the canonical shape definitions; this module turns those models
into a JSON Schema 2020-12 dict that the TypeScript side validates against.
The exported schema covers every node type the builder emits because every
model is reachable from :class:`Document` through the discriminated unions,
and Pydantic emits each transitively-reached model under ``$defs``.
"""

from __future__ import annotations

import typing as t

from pydantic import TypeAdapter

from gp_sphinx_astro_builder.models import Document, Symbol, XrefEntry


def export_doctree_schema() -> dict[str, t.Any]:
    """Return the full JSON Schema for :class:`Document`.

    The dict reuses Pydantic's default ``$ref`` template
    (``#/$defs/<ModelName>``) and emits every dependent model under
    ``$defs``.

    Returns
    -------
    dict[str, Any]
        JSON Schema as a Python dict, ready for ``json.dumps``.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.schemas import export_doctree_schema
    >>> schema = export_doctree_schema()
    >>> "TextNode" in schema["$defs"]
    True
    """
    return Document.model_json_schema()


def export_symbol_schema() -> dict[str, t.Any]:
    """Return the full JSON Schema for :class:`Symbol`.

    Symbol's ``docstring_body`` field carries a list of :class:`BlockNode`,
    so Pydantic transitively pulls every doctree node model into ``$defs``
    — meaning this schema covers both the API-symbol shape AND the doctree
    shape used to render docstrings. The Astro side validates entries in
    ``src/content/api/symbols.json`` against this schema.

    Returns
    -------
    dict[str, Any]
        JSON Schema as a Python dict, ready for ``json.dumps``.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.schemas import export_symbol_schema
    >>> schema = export_symbol_schema()
    >>> "Parameter" in schema["$defs"]
    True
    >>> "TextNode" in schema["$defs"]
    True
    """
    return Symbol.model_json_schema()


_XREF_INDEX_TYPE_ADAPTER: TypeAdapter[list[XrefEntry]] = TypeAdapter(list[XrefEntry])


def export_xref_index_schema() -> dict[str, t.Any]:
    """Return the JSON Schema for the ``xref-index.json`` array.

    The xref index is shipped as a flat array of :class:`XrefEntry`
    objects, so the top-level shape is ``{"type": "array", "items":
    {"$ref": "#/$defs/XrefEntry"}}`` and the ``XrefEntry`` model lives
    under ``$defs``. The Astro side validates the array directly through
    a ``z.array(xrefEntrySchema)`` schema.

    Returns
    -------
    dict[str, Any]
        JSON Schema as a Python dict, ready for ``json.dumps``.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.schemas import export_xref_index_schema
    >>> schema = export_xref_index_schema()
    >>> schema["type"]
    'array'
    >>> "XrefEntry" in schema["$defs"]
    True
    """
    return _XREF_INDEX_TYPE_ADAPTER.json_schema()
