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
    source_repository = "https://github.com/git-pull/demo"
    astro_source_root = r"__SCENARIO_SRCDIR__"
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
    # The signature field must hold ONLY the parameter list (and, when
    # present, the return annotation prefixed with " -> ") — never the
    # module/qualname (already in symbol['module']/['qualname']) and
    # never the api-style extension's inline ``objtype`` badge text.
    sig = symbol["signature"]
    assert sig.startswith("("), f"expected sig to start with '(', got {sig!r}"
    assert "merge_demo" not in sig, (
        f"signature must not duplicate the qualname; got {sig!r}"
    )
    assert "function" not in sig, (
        f"signature must not contain the objtype badge text; got {sig!r}"
    )
    # The autofixture function returns ``dict[str, str]`` so the
    # signature should end with the return annotation.
    assert sig.endswith("dict[str, str]"), (
        f"expected sig to end with the return annotation; got {sig!r}"
    )
    # ``Symbol.source`` is populated via ``inspect.getsourcefile`` /
    # ``getsourcelines`` whenever the docs project sets
    # ``source_repository`` and the autodoc target is importable.
    source = symbol["source"]
    assert source is not None, "expected source to be populated"
    assert source["repo"] == "https://github.com/git-pull/demo"
    assert source["path"] == "demo_api.py"
    # ``def merge_demo`` lands on the second line of the dedented module
    # source (after ``from __future__ import annotations`` + blank).
    assert source["line"] >= 1


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


_BADGE_CONF_PY = textwrap.dedent(
    """\
    project = "Demo"
    extensions = ["sphinx_ux_badges", "gp_sphinx_astro_builder"]
    master_doc = "index"
    exclude_patterns = ["_build"]
    """,
)

_BADGE_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    Status placeholder.
    """,
)


@pytest.mark.integration
def test_astro_builder_emits_badge_node_via_extension_json_visitor(
    tmp_path: pathlib.Path,
) -> None:
    """``sphinx-ux-badges``' JSON visitor injects ``BadgeNode`` into the doctree.

    The fixture builds a tiny Sphinx project that wires the
    :mod:`sphinx_ux_badges` extension. Since badges are produced
    programmatically (no public directive), we monkey-patch the doctree
    after the build to inject one ``BadgeNode``, run the translator
    explicitly, and assert the JSON output contains the expected
    ``badge`` entry.
    """
    from docutils import nodes  # noqa: PLC0415

    from sphinx_ux_badges import BadgeNode as DocutilsBadge  # noqa: PLC0415

    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("conf.py", _BADGE_CONF_PY),
            ScenarioFile("index.rst", _BADGE_INDEX_RST),
        ),
    )
    result = build_isolated_sphinx_result(cache_root, tmp_path, scenario)

    # Inject a BadgeNode into the built doctree, then re-run the translator.
    doctree = result.app.env.get_doctree("index")
    paragraphs = list(doctree.findall(nodes.paragraph))
    assert paragraphs, "expected at least one paragraph in the built doctree"
    paragraphs[0] += DocutilsBadge(
        "ok",
        badge_tooltip="All good",
        badge_size="sm",
    )
    builder = result.app.builder
    builder.write_doc("index", doctree)

    output_path = result.outdir / "src" / "content" / "docs" / "index.json"
    document = json.loads(output_path.read_text("utf-8"))
    badges = [
        child
        for paragraph in document["tree"]["children"]
        if paragraph.get("type") == "paragraph"
        for child in paragraph.get("children", [])
        if child.get("type") == "badge"
    ]
    assert len(badges) == 1
    badge = badges[0]
    assert badge["text"] == "ok"
    assert badge["tooltip"] == "All good"
    assert badge["size"] == "sm"
    assert badge["style"] == "full"


@pytest.mark.integration
def test_astro_builder_emits_content_config_ts(
    tmp_path: pathlib.Path,
) -> None:
    """``finish()`` writes ``src/content.config.ts`` with the canonical wiring."""
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("conf.py", _CONF_PY),
            ScenarioFile("index.rst", _INDEX_RST),
        ),
    )
    result = build_isolated_sphinx_result(cache_root, tmp_path, scenario)

    config_path = result.outdir / "src" / "content.config.ts"
    assert config_path.exists(), (
        f"expected {config_path} to be emitted; "
        f"outdir contents: {list(result.outdir.rglob('*'))}"
    )

    source = config_path.read_text("utf-8")
    assert "export const collections" in source
    assert "docs: defineCollection" in source
    assert "api: defineCollection" in source
    assert "xrefs: defineCollection" in source


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


_ARGPARSE_CONF_PY = textwrap.dedent(
    """\
    project = "Demo"
    extensions = ["sphinx_autodoc_argparse", "gp_sphinx_astro_builder"]
    master_doc = "index"
    exclude_patterns = ["_build"]
    """,
)

_ARGPARSE_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    CLI placeholder.
    """,
)


@pytest.mark.integration
def test_astro_builder_emits_cli_command_via_argparse_visitor(
    tmp_path: pathlib.Path,
) -> None:
    """``sphinx-autodoc-argparse``'s JSON visitors emit a ``cliCommand`` block.

    The fixture builds a tiny Sphinx project that wires the
    :mod:`sphinx_autodoc_argparse` extension. Argparse nodes are
    normally produced by the directive against a real argparse parser;
    here we inject the six custom node types into the built doctree
    directly, re-run the translator, and assert that each emits the
    expected ``cliCommand`` JSON shape with the right ``component``
    discriminator.
    """
    from sphinx_autodoc_argparse.nodes import (  # noqa: PLC0415
        argparse_argument,
        argparse_group,
        argparse_program,
        argparse_subcommand,
        argparse_subcommands,
        argparse_usage,
    )

    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("conf.py", _ARGPARSE_CONF_PY),
            ScenarioFile("index.rst", _ARGPARSE_INDEX_RST),
        ),
    )
    result = build_isolated_sphinx_result(cache_root, tmp_path, scenario)

    from docutils import nodes  # noqa: PLC0415

    doctree = result.app.env.get_doctree("index")
    section = doctree.children[0]
    assert isinstance(section, nodes.Element)

    program = argparse_program()
    program["prog"] = "myapp"

    usage = argparse_usage()
    usage["usage"] = "myapp [-h] [--verbose] cmd"
    program += usage

    group = argparse_group()
    group["title"] = "Options"
    group["description"] = "General options"

    arg = argparse_argument()
    arg["names"] = ["-v", "--verbose"]
    arg["help"] = "Increase output verbosity"
    arg["default"] = "False"
    arg["choices"] = []
    arg["required"] = False
    arg["metavar"] = "LEVEL"
    group += arg
    program += group

    subcommands = argparse_subcommands()
    subcommands["title"] = "Commands"
    sub = argparse_subcommand()
    sub["name"] = "build"
    sub["aliases"] = ["b"]
    sub["help"] = "Build the project"
    subcommands += sub
    program += subcommands

    section += program

    builder = result.app.builder
    builder.write_doc("index", doctree)

    output_path = result.outdir / "src" / "content" / "docs" / "index.json"
    document = json.loads(output_path.read_text("utf-8"))

    cli_blocks = [
        child
        for child in document["tree"]["children"]
        if child.get("type") == "cliCommand"
    ]
    assert len(cli_blocks) == 1, (
        f"expected one top-level cliCommand block, got: {cli_blocks}"
    )
    program_block = cli_blocks[0]
    assert program_block["component"] == "program"
    assert program_block["prog"] == "myapp"

    components = [node["component"] for node in _walk_cli_command(program_block)]
    assert components == [
        "program",
        "usage",
        "group",
        "argument",
        "subcommands",
        "subcommand",
    ]

    by_component = {
        node["component"]: node for node in _walk_cli_command(program_block)
    }
    assert by_component["usage"]["usage"] == "myapp [-h] [--verbose] cmd"
    assert by_component["group"]["title"] == "Options"
    assert by_component["argument"]["names"] == ["-v", "--verbose"]
    assert by_component["argument"]["metavar"] == "LEVEL"
    assert by_component["subcommand"]["name"] == "build"
    assert by_component["subcommand"]["aliases"] == ["b"]

    # The whole tree must validate through the Pydantic Document model.
    Document.model_validate(document)


def _walk_cli_command(node: dict[str, t.Any]) -> t.Iterator[dict[str, t.Any]]:
    """Pre-order walk of nested ``cliCommand`` blocks."""
    if node.get("type") == "cliCommand":
        yield node
        for child in node.get("children", []):
            yield from _walk_cli_command(child)


_GRID_CARD_CONF_PY = textwrap.dedent(
    """\
    project = "Demo"
    extensions = ["myst_parser", "sphinx_design", "gp_sphinx_astro_builder"]
    master_doc = "index"
    exclude_patterns = ["_build"]
    myst_enable_extensions = ["colon_fence"]
    """,
)

_GRID_CARD_INDEX_MD = textwrap.dedent(
    """\
    # Demo

    :::{grid} 1

    :::{grid-item-card} sphinx-ux-badges
    :link: target
    :link-type: doc

    Badge primitives, colour palette, and CSS infrastructure.
    :::

    :::
    """,
)

_GRID_CARD_TARGET_MD = "# Target\n\nhi\n"


@pytest.mark.integration
def test_astro_builder_handles_sphinx_design_grid_item_card(
    tmp_path: pathlib.Path,
) -> None:
    """A sphinx_design ``grid-item-card`` validates as a Document.

    sphinx-design wraps card content in nested ``container`` nodes plus
    a ``PassthroughTextElement`` for the title. Without explicit
    handlers, the inline title text and the link reference leak into
    the surrounding section's block-children slot and break Pydantic
    validation.
    """
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("conf.py", _GRID_CARD_CONF_PY),
            ScenarioFile("index.md", _GRID_CARD_INDEX_MD),
            ScenarioFile("target.md", _GRID_CARD_TARGET_MD),
        ),
    )
    result = build_isolated_sphinx_result(cache_root, tmp_path, scenario)

    output_path = result.outdir / "src" / "content" / "docs" / "index.json"
    assert output_path.exists(), (
        f"expected {output_path} to be emitted; "
        f"outdir contents: {list(result.outdir.rglob('*'))}"
    )
    document = Document.model_validate_json(output_path.read_text("utf-8"))
    assert document.id == "index"


_NUMPY_DOCSTRING_MODULE_SOURCE = textwrap.dedent(
    '''\
    from __future__ import annotations


    def shape(width: int, height: int) -> int:
        """Compute a rectangle area.

        Parameters
        ----------
        width : int
            The horizontal extent.
        height : int
            The vertical extent.

        Returns
        -------
        int
            The product of width and height.

        Examples
        --------
        >>> shape(3, 4)
        12
        """
        return width * height
    ''',
)

_NUMPY_DOCSTRING_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    project = "Demo"
    extensions = [
        "sphinx.ext.autodoc",
        "sphinx_autodoc_typehints_gp",
        "gp_sphinx_astro_builder",
    ]
    master_doc = "index"
    exclude_patterns = ["_build"]
    """,
)

_NUMPY_DOCSTRING_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    .. autofunction:: numpy_demo.shape
    """,
)


_AUTOCLASS_MODULE_SOURCE = textwrap.dedent(
    '''\
    from __future__ import annotations


    class Widget:
        """A clickable widget for the demo gallery.

        Renders a button that dispatches a custom event on click.
        """

        def __init__(self, label: str) -> None:
            self.label = label
    ''',
)


_AUTOCLASS_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    .. autoclass:: numpy_demo.Widget
       :show-inheritance:
    """,
)


@pytest.mark.integration
def test_astro_builder_skips_bases_paragraph_for_class_summary(
    tmp_path: pathlib.Path,
) -> None:
    """Sphinx's auto-injected ``Bases: <link>`` paragraph must not become the summary.

    Sphinx's autoclass directive prepends a ``Bases: <pending_xref>``
    paragraph to every class's content. The translator extracts the
    first body paragraph as ``docstring_summary``; without filtering,
    classes get ``"Bases: "`` (just the lead-in text, since the
    inline reference is dropped from text-only summary extraction)
    instead of their real docstring summary. That string then leaks
    into the rendered ``__summary__`` paragraph and the OpenGraph
    ``description`` meta tag — visible to readers and search crawlers.
    """
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("numpy_demo.py", _AUTOCLASS_MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _NUMPY_DOCSTRING_CONF_PY.replace(
                    "__SCENARIO_SRCDIR__",
                    SCENARIO_SRCDIR_TOKEN,
                ),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _AUTOCLASS_INDEX_RST),
        ),
    )
    result = build_isolated_sphinx_result(
        cache_root,
        tmp_path,
        scenario,
        purge_modules=("numpy_demo",),
    )

    symbols_path = result.outdir / "src" / "content" / "api" / "symbols.json"
    symbols = json.loads(symbols_path.read_text("utf-8"))
    widget = next(s for s in symbols if s["id"] == "numpy_demo.Widget")
    assert widget["docstring_summary"] == "A clickable widget for the demo gallery.", (
        f"expected real class summary; got {widget['docstring_summary']!r}"
    )


@pytest.mark.integration
def test_astro_builder_emits_field_list_as_definition_list(
    tmp_path: pathlib.Path,
) -> None:
    """A NumPy-style docstring with Parameters/Returns rubrics validates.

    Sphinx's ``sphinx_autodoc_typehints_gp`` extension parses NumPy
    docstring sections into ``field_list / field / field_name /
    field_body`` chains. Without explicit handling, the bare ``Text``
    children of ``field_name`` ("Parameters", "Returns", …) leak into
    the surrounding block context as inline ``text`` nodes and fail
    Pydantic validation against the ``BlockNode`` discriminator.
    """
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("numpy_demo.py", _NUMPY_DOCSTRING_MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _NUMPY_DOCSTRING_CONF_PY.replace(
                    "__SCENARIO_SRCDIR__",
                    SCENARIO_SRCDIR_TOKEN,
                ),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _NUMPY_DOCSTRING_INDEX_RST),
        ),
    )
    result = build_isolated_sphinx_result(
        cache_root,
        tmp_path,
        scenario,
        purge_modules=("numpy_demo",),
    )

    symbols_path = result.outdir / "src" / "content" / "api" / "symbols.json"
    assert symbols_path.exists(), (
        f"expected {symbols_path} to be emitted; "
        f"outdir contents: {list(result.outdir.rglob('*'))}"
    )
    symbols = json.loads(symbols_path.read_text("utf-8"))
    [symbol] = symbols

    body = symbol["docstring_body"]
    types = [block["type"] for block in body]
    # Expected shape: summary paragraph; then the field_list capturing
    # Parameters / Returns / Return type; then the Examples rubric (now
    # promoted to a first-class ``rubric`` block per cycle 65) and the
    # doctest block beneath it.
    assert types == ["paragraph", "definitionList", "rubric", "literalBlock"], (
        f"expected summary, definitionList, examples rubric, and a doctest "
        f"literalBlock; got block types: {types}"
    )
    assert body[2]["text"] == "Examples"

    items = body[1]["children"]
    terms = [
        "".join(t.get("value", "") for t in item["term"] if t.get("type") == "text")
        for item in items
    ]
    assert "Parameters" in terms
    assert "Returns" in terms

    # The Examples rubric carries its label as a top-level ``text``
    # field on the rubric block (cycle 65). The doctest_block follows.
    assert body[2]["text"] == "Examples"
    assert body[3]["language"] == "python"
    assert "shape(3, 4)" in body[3]["code"]


_MULTI_PAGE_CONF_PY = textwrap.dedent(
    """\
    project = "Multi"
    extensions = ["gp_sphinx_astro_builder"]
    master_doc = "index"
    exclude_patterns = ["_build"]
    """,
)

_MULTI_PAGE_INDEX_RST = textwrap.dedent(
    """\
    Multi
    =====

    Welcome.

    .. toctree::

       guide
       reference
    """,
)

_MULTI_PAGE_GUIDE_RST = textwrap.dedent(
    """\
    Guide
    =====

    See :doc:`reference` for details.
    """,
)

_MULTI_PAGE_REFERENCE_RST = textwrap.dedent(
    """\
    Reference
    =========

    See :doc:`guide` to learn first.
    """,
)


@pytest.mark.integration
def test_astro_builder_emits_one_json_per_page(
    tmp_path: pathlib.Path,
) -> None:
    r"""A toctree spanning three docs emits one JSON file per page.

    This is the smallest end-to-end shape that exercises multi-page
    behavior the dogfood site relies on: each source doc becomes a
    ``src/content/docs/<slug>.json`` file, every emitted JSON validates
    as a ``Document``, and internal ``:doc:`...``` cross-references
    resolve to anchors that the renderer can dispatch on.
    """
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = SphinxScenario(
        buildername="astro",
        files=(
            ScenarioFile("conf.py", _MULTI_PAGE_CONF_PY),
            ScenarioFile("index.rst", _MULTI_PAGE_INDEX_RST),
            ScenarioFile("guide.rst", _MULTI_PAGE_GUIDE_RST),
            ScenarioFile("reference.rst", _MULTI_PAGE_REFERENCE_RST),
        ),
    )
    result = build_isolated_sphinx_result(cache_root, tmp_path, scenario)

    docs_dir = result.outdir / "src" / "content" / "docs"
    emitted = sorted(p.name for p in docs_dir.glob("*.json"))
    assert emitted == ["guide.json", "index.json", "reference.json"], (
        f"expected one JSON per page; got {emitted}"
    )

    # Each emitted JSON file must validate against the Pydantic Document
    # contract — we treat schema parity as a hard gate, not a soft one.
    for slug in ("index", "guide", "reference"):
        doc = Document.model_validate_json(
            (docs_dir / f"{slug}.json").read_text("utf-8"),
        )
        assert doc.id == slug

    # The :doc:`reference` xref in guide.rst must turn into a reference
    # node whose href points at the sibling page.
    guide = json.loads((docs_dir / "guide.json").read_text("utf-8"))
    refs = [
        child
        for paragraph in guide["tree"]["children"]
        if paragraph.get("type") == "paragraph"
        for child in paragraph.get("children", [])
        if child.get("type") == "reference"
    ]
    assert len(refs) >= 1, (
        f"expected at least one reference in guide.json; tree: {guide['tree']}"
    )
    hrefs = {ref["href"] for ref in refs}
    assert any("reference" in href for href in hrefs), (
        f"expected a cross-doc href to 'reference'; got: {hrefs}"
    )
