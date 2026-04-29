"""Drift detection for the committed Pydantic JSON Schema fixtures.

The Astro side's parity tests read ``astro/fixtures/{doctree,symbol}.schema.json``
to reconstruct Zod schemas via ``z.fromJSONSchema``. Each fixture is a copy
of what :func:`gp_sphinx_astro_builder.schemas.export_doctree_schema` and
:func:`export_symbol_schema` produce; these tests fail the build if either
live export drifts away from the committed copy. Regenerate with::

    uv run python -c "
    import json
    from gp_sphinx_astro_builder.schemas import (
        export_doctree_schema, export_symbol_schema,
    )
    open('astro/fixtures/doctree.schema.json', 'w').write(
        json.dumps(export_doctree_schema(), indent=2, sort_keys=True) + '\\n'
    )
    open('astro/fixtures/symbol.schema.json', 'w').write(
        json.dumps(export_symbol_schema(), indent=2, sort_keys=True) + '\\n'
    )
    "
"""

from __future__ import annotations

import json
import pathlib

from gp_sphinx_astro_builder.schemas import (
    export_doctree_schema,
    export_symbol_schema,
)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_FIXTURES_DIR = _REPO_ROOT / "astro" / "fixtures"


def test_pydantic_doctree_schema_fixture_matches_live_export() -> None:
    """The committed doctree fixture must match the live Pydantic export."""
    live = export_doctree_schema()
    committed = json.loads(
        (_FIXTURES_DIR / "doctree.schema.json").read_text("utf-8"),
    )
    assert live == committed, (
        "astro/fixtures/doctree.schema.json is stale; "
        "regenerate it from gp_sphinx_astro_builder.schemas.export_doctree_schema."
    )


def test_pydantic_symbol_schema_fixture_matches_live_export() -> None:
    """The committed symbol fixture must match the live Pydantic export."""
    live = export_symbol_schema()
    committed = json.loads(
        (_FIXTURES_DIR / "symbol.schema.json").read_text("utf-8"),
    )
    assert live == committed, (
        "astro/fixtures/symbol.schema.json is stale; "
        "regenerate it from gp_sphinx_astro_builder.schemas.export_symbol_schema."
    )
