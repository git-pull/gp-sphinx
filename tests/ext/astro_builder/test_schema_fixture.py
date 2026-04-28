"""Drift detection for the committed Pydantic JSON Schema fixture.

The Astro side's parity test reads ``astro/fixtures/doctree.schema.json`` to
reconstruct a Zod schema via ``z.fromJSONSchema``. That fixture is a copy of
what :func:`gp_sphinx_astro_builder.schemas.export_doctree_schema` produces;
this test fails the build if the live export drifts away from the committed
copy. Regenerate with::

    uv run python -c "
    import json
    from gp_sphinx_astro_builder.schemas import export_doctree_schema
    print(json.dumps(export_doctree_schema(), indent=2, sort_keys=True))
    " > astro/fixtures/doctree.schema.json
"""

from __future__ import annotations

import json
import pathlib

from gp_sphinx_astro_builder.schemas import export_doctree_schema

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_FIXTURE_PATH = _REPO_ROOT / "astro" / "fixtures" / "doctree.schema.json"


def test_pydantic_schema_fixture_matches_live_export() -> None:
    """The committed fixture must match the live Pydantic export.

    Failure means ``models.py`` changed without re-running the fixture
    regeneration command shown in this module's docstring.
    """
    live = export_doctree_schema()
    committed = json.loads(_FIXTURE_PATH.read_text("utf-8"))
    assert live == committed, (
        "astro/fixtures/doctree.schema.json is stale; "
        "regenerate it from gp_sphinx_astro_builder.schemas.export_doctree_schema."
    )
