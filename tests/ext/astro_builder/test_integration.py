"""Integration tests for :class:`gp_sphinx_astro_builder.builder.AstroBuilder`.

A real Sphinx app is constructed against a tiny synthetic project, the
``astro`` builder runs end-to-end, and the emitted JSON file is validated
through the Pydantic ``Document`` model. These tests are marked
``integration`` so the unit-test layer stays microsecond-fast.
"""

from __future__ import annotations

import json
import pathlib
import textwrap
import typing as t

import pytest

from gp_sphinx_astro_builder.models import (
    Document,
    EmphasisNode,
    ParagraphNode,
    TextNode,
)
from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SphinxScenario,
    build_isolated_sphinx_result,
    derive_sphinx_scenario_cache_root,
)

if t.TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion


_CONF_PY = textwrap.dedent(
    """\
    project = "Demo"
    extensions = ["gp_sphinx_astro_builder"]
    master_doc = "index"
    exclude_patterns = ["_build"]
    """,
)

_INDEX_RST = textwrap.dedent(
    """\
    Hello world
    ===========

    Hello *world*.
    """,
)


@pytest.mark.integration
def test_astro_builder_emits_pydantic_valid_document(
    tmp_path: pathlib.Path,
) -> None:
    """An end-to-end build emits a JSON file that validates as a ``Document``."""
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("conf.py", _CONF_PY),
            ScenarioFile("index.rst", _INDEX_RST),
        ),
    )
    result = build_isolated_sphinx_result(cache_root, tmp_path, scenario)

    output_path = result.outdir / "src" / "content" / "docs" / "index.json"
    assert output_path.exists(), (
        f"expected {output_path} to be emitted, "
        f"outdir contents: {list(result.outdir.rglob('*'))}"
    )

    document = Document.model_validate_json(output_path.read_text("utf-8"))
    assert document.id == "index"
    assert document.title == "Hello world"
    assert document.tree.id == "hello-world"
    assert document.tree.title == [TextNode(type="text", value="Hello world")]
    assert len(document.tree.children) == 1
    paragraph = document.tree.children[0]
    assert isinstance(paragraph, ParagraphNode)
    # "Hello *world*." → text("Hello "), emphasis(text("world")), text(".")
    assert len(paragraph.children) == 3
    assert paragraph.children[0] == TextNode(type="text", value="Hello ")
    assert isinstance(paragraph.children[1], EmphasisNode)
    assert paragraph.children[1].children == [TextNode(type="text", value="world")]
    assert paragraph.children[2] == TextNode(type="text", value=".")


@pytest.mark.integration
def test_astro_builder_emits_doctree_schema_in_finish(
    tmp_path: pathlib.Path,
) -> None:
    """``finish()`` writes ``schemas/doctree.schema.json`` into the outdir."""
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("conf.py", _CONF_PY),
            ScenarioFile("index.rst", _INDEX_RST),
        ),
    )
    result = build_isolated_sphinx_result(cache_root, tmp_path, scenario)

    schema_path = result.outdir / "schemas" / "doctree.schema.json"
    assert schema_path.exists(), (
        f"expected {schema_path} to be emitted; "
        f"outdir contents: {list(result.outdir.rglob('*'))}"
    )

    schema = json.loads(schema_path.read_text("utf-8"))
    assert isinstance(schema, dict)
    assert "TextNode" in schema.get("$defs", {})
    assert "AdmonitionNode" in schema.get("$defs", {})


_AUTODOC_MODULE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations


    def merge_demo(project: str, version: str = "0.0.0") -> dict[str, str]:
        \"\"\"Merge a tiny pseudo-config payload.

        Returns
        -------
        dict[str, str]
            The merged payload, unchanged.
        \"\"\"
        return {"project": project, "version": version}
    """,
)

_AUTODOC_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    project = "Demo"
    extensions = ["sphinx.ext.autodoc", "gp_sphinx_astro_builder"]
    master_doc = "index"
    exclude_patterns = ["_build"]
    """,
)

_AUTODOC_INDEX_RST = textwrap.dedent(
    """\
    Demo API
    ========

    .. autofunction:: demo_api.merge_demo
    """,
)


@pytest.mark.integration
def test_astro_builder_emits_symbols_json_for_autofunction(
    tmp_path: pathlib.Path,
) -> None:
    """An autodoc'd function lands as one entry in ``src/content/api/symbols.json``."""
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("demo_api.py", _AUTODOC_MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _AUTODOC_CONF_PY.replace(
                    "__SCENARIO_SRCDIR__",
                    SCENARIO_SRCDIR_TOKEN,
                ),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _AUTODOC_INDEX_RST),
        ),
    )
    result = build_isolated_sphinx_result(
        cache_root,
        tmp_path,
        scenario,
        purge_modules=("demo_api",),
    )

    symbols_path = result.outdir / "src" / "content" / "api" / "symbols.json"
    assert symbols_path.exists(), (
        f"expected {symbols_path} to be emitted; "
        f"outdir contents: {list(result.outdir.rglob('*'))}"
    )

    symbols = json.loads(symbols_path.read_text("utf-8"))
    assert isinstance(symbols, list)
    assert len(symbols) == 1
    [symbol] = symbols
    assert symbol["id"] == "demo_api.merge_demo"
    assert symbol["kind"] == "function"
    assert symbol["module"] == "demo_api"
    assert "merge_demo" in symbol["name"]
    assert symbol["docstring_summary"].startswith("Merge a tiny pseudo-config payload")


@pytest.mark.integration
def test_astro_builder_replaces_desc_with_symbol_ref_node(
    tmp_path: pathlib.Path,
) -> None:
    """The doctree JSON contains a ``symbolRef`` placeholder, not raw ``desc``."""
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("demo_api.py", _AUTODOC_MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _AUTODOC_CONF_PY.replace(
                    "__SCENARIO_SRCDIR__",
                    SCENARIO_SRCDIR_TOKEN,
                ),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _AUTODOC_INDEX_RST),
        ),
    )
    result = build_isolated_sphinx_result(
        cache_root,
        tmp_path,
        scenario,
        purge_modules=("demo_api",),
    )

    output_path = result.outdir / "src" / "content" / "docs" / "index.json"
    document = json.loads(output_path.read_text("utf-8"))
    children = document["tree"]["children"]
    symbol_refs = [c for c in children if c.get("type") == "symbolRef"]
    assert len(symbol_refs) == 1
    assert symbol_refs[0] == {
        "type": "symbolRef",
        "symbolId": "demo_api.merge_demo",
    }


@pytest.mark.integration
def test_astro_builder_emits_xref_index_json_for_autodoc_symbol(
    tmp_path: pathlib.Path,
) -> None:
    """An autodoc'd function lands in ``xref-index.json`` as one entry."""
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("demo_api.py", _AUTODOC_MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _AUTODOC_CONF_PY.replace(
                    "__SCENARIO_SRCDIR__",
                    SCENARIO_SRCDIR_TOKEN,
                ),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _AUTODOC_INDEX_RST),
        ),
    )
    result = build_isolated_sphinx_result(
        cache_root,
        tmp_path,
        scenario,
        purge_modules=("demo_api",),
    )

    xref_path = result.outdir / "xref-index.json"
    assert xref_path.exists(), (
        f"expected {xref_path} to be emitted; "
        f"outdir contents: {list(result.outdir.rglob('*'))}"
    )

    entries = json.loads(xref_path.read_text("utf-8"))
    assert isinstance(entries, list)
    function_entries = [e for e in entries if e.get("target") == "demo_api.merge_demo"]
    assert len(function_entries) == 1
    [entry] = function_entries
    assert entry["domain"] == "py"
    assert entry["role"] in {"function", "func"}
    assert entry["id"].endswith("demo_api.merge_demo")


@pytest.mark.integration
def test_astro_builder_emits_objects_inv_round_trippable(
    tmp_path: pathlib.Path,
) -> None:
    """The emitted ``objects.inv`` parses through Sphinx's inventory loader."""
    from sphinx.util.inventory import InventoryFile  # noqa: PLC0415

    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("demo_api.py", _AUTODOC_MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _AUTODOC_CONF_PY.replace(
                    "__SCENARIO_SRCDIR__",
                    SCENARIO_SRCDIR_TOKEN,
                ),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _AUTODOC_INDEX_RST),
        ),
    )
    result = build_isolated_sphinx_result(
        cache_root,
        tmp_path,
        scenario,
        purge_modules=("demo_api",),
    )

    inv_path = result.outdir / "objects.inv"
    assert inv_path.exists()

    with inv_path.open("rb") as f:
        inventory = InventoryFile.load(
            f, "https://example.com", lambda base, slug: f"{base}/{slug}"
        )

    # Inventory is a dict[type -> dict[name -> InventoryItem]]; the python
    # function we autodoc'd should show up under py:function (or py:func).
    assert any(
        "demo_api.merge_demo" in inventory.get(type_key, {})
        for type_key in ("py:function", "py:func")
    ), f"expected demo_api.merge_demo in inventory; got types: {list(inventory.keys())}"


@pytest.mark.integration
def test_astro_builder_emission_matches_snapshot(
    tmp_path: pathlib.Path,
    snapshot: SnapshotAssertion,
) -> None:
    """Emitted JSON is byte-stable against a syrupy snapshot."""
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("conf.py", _CONF_PY),
            ScenarioFile("index.rst", _INDEX_RST),
        ),
    )
    result = build_isolated_sphinx_result(cache_root, tmp_path, scenario)

    output_path = result.outdir / "src" / "content" / "docs" / "index.json"
    assert output_path.read_text("utf-8") == snapshot
