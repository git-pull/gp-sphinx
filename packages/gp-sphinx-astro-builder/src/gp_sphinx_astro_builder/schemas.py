"""JSON Schema export for the doctree wire format.

Pydantic owns the canonical shape definitions; this module turns those models
into a JSON Schema 2020-12 dict that the TypeScript side validates against.
The exported schema covers every node type the builder emits because every
model is reachable from :class:`Document` through the discriminated unions,
and Pydantic emits each transitively-reached model under ``$defs``.
"""

from __future__ import annotations

import typing as t

from gp_sphinx_astro_builder.models import Document


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
