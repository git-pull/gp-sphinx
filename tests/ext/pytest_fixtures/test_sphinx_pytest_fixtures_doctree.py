"""Doctree- and store-level tests for sphinx_autodoc_pytest_fixtures."""

from __future__ import annotations

import pathlib
import textwrap
import typing as t

import pytest
from docutils import nodes
from sphinx import addnodes
from sphinx_autodoc_layout._nodes import api_component

from tests._snapshots import normalize_warning_text
from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SphinxScenario,
    build_shared_sphinx_result,
    get_doctree,
)
from tests.ext.pytest_fixtures._scenario_support import (
    FIXTURE_MOD_SOURCE,
    build_fixture_result,
    render_conf_py,
)

if t.TYPE_CHECKING:
    from sphinx.domains.python import PythonDomain

    from tests._sphinx_scenarios import SharedSphinxResult

pytestmark = pytest.mark.integration

_AUTOFIXTURES_SMOKE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations
    import pytest

    class Server:
        \"\"\"A fake server.\"\"\"

    @pytest.fixture(scope="session")
    def my_server() -> Server:
        \"\"\"Return a fake server for testing.\"\"\"
        return Server()

    @pytest.fixture
    def my_client(my_server: Server) -> str:
        \"\"\"Return a fake client connected to *my_server*.\"\"\"
        return f"client@{my_server}"

    @pytest.fixture(name="renamed_fixture")
    def _internal_name() -> str:
        \"\"\"Fixture with a name alias — injected as 'renamed_fixture'.\"\"\"
        return "renamed"
    """,
)

_AUTOFIXTURE_INDEX_SMOKE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations
    import pytest

    class Server:
        \"\"\"A fake server.\"\"\"

    @pytest.fixture(scope="session")
    def my_server() -> Server:
        \"\"\"Return a fake server for testing.\"\"\"
        return Server()

    @pytest.fixture
    def plain_fixture(my_server: Server) -> str:
        \"\"\"Uses :fixture:`my_server` to build a plain resource fixture.\"\"\"
        return "plain"

    @pytest.fixture
    def TestServer() -> type[Server]:
        \"\"\"Return the Server class for direct instantiation (factory fixture).\"\"\"
        return Server

    @pytest.fixture(autouse=True)
    def auto_cleanup() -> None:
        \"\"\"Runs automatically before every test.\"\"\"
        return None
    """,
)


@pytest.fixture(scope="module")
def default_dummy_result(
    spf_doctree_root: pathlib.Path,
) -> SharedSphinxResult:
    """Build the default dummy-builder fixture scenario once per module."""
    return build_fixture_result(
        spf_doctree_root / "default-dummy",
        buildername="dummy",
        confoverrides={"pytest_fixture_lint_level": "none"},
    )


@pytest.fixture(scope="module")
def autofixtures_usage_result(
    spf_doctree_root: pathlib.Path,
) -> SharedSphinxResult:
    """Build one dummy MyST+usage scenario for autofixtures and short-name refs."""
    return build_fixture_result(
        spf_doctree_root / "autofixtures-with-usage",
        buildername="dummy",
        fixture_source=_AUTOFIXTURES_SMOKE_SOURCE,
        index_rst=textwrap.dedent(
            """\
            Test fixtures
            =============

            .. py:module:: fixture_mod

            .. autofixtures:: fixture_mod

            Usage
            -----

            See :fixture:`my_server` for the server fixture.
            """,
        ),
        confoverrides={"pytest_fixture_lint_level": "none"},
    )


@pytest.fixture(scope="module")
def myst_smoke_result(spf_doctree_root: pathlib.Path) -> SharedSphinxResult:
    """Build one shared MyST scenario for both auto-pytest-plugin smoke checks."""
    scenario_root = spf_doctree_root / "shared-myst-smokes"
    conf_text = render_conf_py(
        scenario_root / "src",
        extensions=[
            "myst_parser",
            "sphinx.ext.autodoc",
            "sphinx_autodoc_pytest_fixtures",
        ],
    ).replace(
        str(scenario_root / "src"),
        SCENARIO_SRCDIR_TOKEN,
    )
    scenario = SphinxScenario(
        buildername="dummy",
        files=(
            ScenarioFile("fixture_mod.py", _AUTOFIXTURES_SMOKE_SOURCE),
            ScenarioFile("conf.py", conf_text, substitute_srcdir=True),
            ScenarioFile(
                "index.rst",
                textwrap.dedent(
                    """\
                    Test fixtures
                    =============

                    .. toctree::

                       plugin
                       autofixtures
                    """,
                ),
            ),
            ScenarioFile(
                "plugin.md",
                textwrap.dedent(
                    """\
                    # Test fixtures

                    :::{auto-pytest-plugin} fixture_mod
                    :project: fixture-demo
                    :package: fixture-demo
                    :summary: fixture-demo ships a pytest plugin for local test setup.
                    :tests-url: https://example.com/fixture-demo/tests

                    ## Recommended fixtures

                    Use this page when you want generated fixture docs and authored notes.
                    :::
                    """,
                ),
            ),
            ScenarioFile(
                "autofixtures.md",
                textwrap.dedent(
                    """\
                    # Test fixtures

                    :::{eval-rst}
                    .. py:module:: fixture_mod
                    :::

                    :::{autofixtures} fixture_mod
                    :order: source
                    :::
                    """,
                ),
            ),
        ),
        confoverrides={
            "pytest_fixture_lint_level": "none",
            "myst_enable_extensions": ["colon_fence"],
        },
    )
    return build_shared_sphinx_result(
        spf_doctree_root,
        scenario,
        purge_modules=("fixture_mod",),
    )


def _find_fixture_desc(doctree: nodes.Node, target_id: str) -> addnodes.desc:
    """Return the fixture description with signature ``target_id``."""
    for desc in doctree.findall(addnodes.desc):
        sig = next(desc.findall(addnodes.desc_signature), None)
        if sig is None:
            continue
        if target_id in sig.get("ids", []):
            return desc
    msg = f"fixture desc {target_id!r} not found"
    raise AssertionError(msg)


def _find_first_table(doctree: nodes.Node) -> nodes.table:
    """Return the first table in ``doctree``."""
    table = next(doctree.findall(nodes.table), None)
    if table is None:
        raise AssertionError("expected a table in doctree")
    return table


def _fixture_order(doctree: nodes.Node) -> list[str]:
    """Return fixture ids in document order."""
    fixture_ids: list[str] = []
    for sig in doctree.findall(addnodes.desc_signature):
        ids = sig.get("ids", [])
        if ids:
            fixture_ids.append(ids[0])
    return fixture_ids


def _content_section_names(desc_node: addnodes.desc) -> list[str]:
    """Return shared API section names for one fixture description."""
    content = next(desc_node.findall(addnodes.desc_content), None)
    if content is None:
        return []
    return [
        str(child.get("name"))
        for child in content.children
        if isinstance(child, api_component)
    ]


def test_default_fixture_store_and_domain_contract(
    default_dummy_result: SharedSphinxResult,
) -> None:
    """Default synthetic fixture scenario populates domain and store indices."""
    domain = t.cast("PythonDomain", default_dummy_result.app.env.get_domain("py"))
    objects = domain.data["objects"]

    assert (
        normalize_warning_text(
            default_dummy_result.warnings,
            roots=(default_dummy_result.srcdir, default_dummy_result.outdir),
        )
        == ""
    )
    assert "fixture_mod.my_server" in objects
    assert objects["fixture_mod.my_server"].objtype == "fixture"

    fixture_keys = {
        name for name, entry in objects.items() if entry.objtype == "fixture"
    }
    assert "fixture_mod.renamed_fixture" in fixture_keys
    assert "fixture_mod._internal_name" not in fixture_keys

    store = default_dummy_result.app.env.domaindata["sphinx_autodoc_pytest_fixtures"]
    assert store["reverse_deps"]["fixture_mod.my_server"] == [
        "fixture_mod.my_client",
        "fixture_mod.yield_server",
    ]
    assert "fixture_mod.auto_cleanup" not in store["reverse_deps"]


def test_default_fixture_post_transform_snapshot(
    default_dummy_result: SharedSphinxResult,
    snapshot_doctree,
) -> None:
    """Snapshot the transformed default fixture page contract."""
    doctree = get_doctree(default_dummy_result, "index", post_transforms=True)

    snapshot_doctree(
        doctree,
        name="default_fixture_page",
        roots=(default_dummy_result.srcdir, default_dummy_result.outdir),
    )


def test_default_fixture_sections_use_shared_fact_region(
    default_dummy_result: SharedSphinxResult,
) -> None:
    """Fixture pages wrap metadata field lists in the shared facts region."""
    doctree = get_doctree(default_dummy_result, "index", post_transforms=True)
    fixture_desc = _find_fixture_desc(doctree, "fixture_mod.my_server")

    assert "api-facts" in _content_section_names(fixture_desc)


def test_manual_directive_without_module_registers_unqualified_name(
    spf_doctree_root: pathlib.Path,
) -> None:
    """Bare manual ``py:fixture`` directives register under the unqualified name."""
    index_rst = textwrap.dedent(
        """\
        Manual
        ======

        .. py:fixture:: bare_server

           Bare server docs.
        """,
    )
    result = build_fixture_result(
        spf_doctree_root / "manual-unqualified",
        buildername="dummy",
        index_rst=index_rst,
        confoverrides={"pytest_fixture_lint_level": "none"},
    )

    domain = t.cast("PythonDomain", result.app.env.get_domain("py"))
    assert "bare_server" in domain.data["objects"]


def test_dependency_rendering_snapshot(
    spf_doctree_root: pathlib.Path,
    snapshot_doctree,
) -> None:
    """Hidden, builtin, and external dependencies render via resolved references."""
    fixture_source = FIXTURE_MOD_SOURCE + textwrap.dedent(
        """\

        @pytest.fixture
        def needs_tmp(tmp_path: "pathlib.Path") -> str:
            \"\"\"Uses tmp_path internally.\"\"\"
            return str(tmp_path)
        """,
    )
    index_rst = textwrap.dedent(
        """\
        Test
        ====

        .. py:module:: fixture_mod

        .. autofixture:: fixture_mod.my_client

        .. autofixture:: fixture_mod.needs_tmp

        .. py:fixture:: my_widget
           :depends: special_dep
        """,
    )
    result = build_fixture_result(
        spf_doctree_root / "dependency-rendering",
        buildername="dummy",
        fixture_source=fixture_source,
        index_rst=index_rst,
        confoverrides={
            "pytest_fixture_lint_level": "none",
            "pytest_fixture_hidden_dependencies": frozenset(
                {"pytestconfig", "my_server"}
            ),
            "pytest_external_fixture_links": {
                "special_dep": "https://example.com/fixtures/special_dep",
            },
        },
    )
    doctree = get_doctree(result, "index", post_transforms=True)

    snapshot_doctree(
        _find_fixture_desc(doctree, "fixture_mod.my_client"),
        name="hidden_dependencies",
        roots=(result.srcdir, result.outdir),
    )
    snapshot_doctree(
        _find_fixture_desc(doctree, "fixture_mod.needs_tmp"),
        name="builtin_dependency_link",
        roots=(result.srcdir, result.outdir),
    )
    snapshot_doctree(
        _find_fixture_desc(doctree, "fixture_mod.my_widget"),
        name="external_dependency_link",
        roots=(result.srcdir, result.outdir),
    )


def test_warning_and_manual_option_snapshot(
    spf_doctree_root: pathlib.Path,
    snapshot_doctree,
    snapshot_warnings,
) -> None:
    """Yield, async, deprecated, replacement, and manual options share one scenario."""
    fixture_source = FIXTURE_MOD_SOURCE + textwrap.dedent(
        """\

        @pytest.fixture
        async def async_resource() -> str:
            \"\"\"An async fixture.\"\"\"
            return "async_value"

        @pytest.fixture
        def simple_yield() -> t.Generator[str, None, None]:
            \"\"\"A yield fixture with no teardown documentation.\"\"\"
            yield "value"

        @pytest.fixture
        def documented_yield() -> t.Generator[str, None, None]:
            \"\"\"A yield fixture with documented teardown.

            Teardown
            --------
            Releases the resource after the test completes.
            \"\"\"
            yield "value"

        @pytest.fixture(params=["bash", "zsh", "fish", "nushell"])
        def shell(request) -> str:
            \"\"\"Fixture parametrized over shell interpreters.\"\"\"
            return request.param
        """,
    )
    index_rst = textwrap.dedent(
        """\
        Test
        ====

        .. py:module:: fixture_mod

        .. py:fixture:: my_server
           :usage: none

        .. autofixture:: fixture_mod.async_resource

        .. autofixture:: fixture_mod.simple_yield

        .. autofixture:: fixture_mod.documented_yield

        .. py:fixture:: yield_server
           :module: fixture_mod
           :teardown:
           :teardown-summary: Shuts down the server and cleans socket files.

        .. py:fixture:: old_server
           :module: fixture_mod
           :deprecated: 2.0
           :replacement: my_server

           An old server fixture.

        .. py:fixture:: old_thing
           :deprecated: 1.5

           An old fixture.

        .. py:fixture:: async_thing
           :async:

           An async fixture.

        .. autofixture:: fixture_mod.shell

        .. py:fixture:: shell_manual
           :params: 'bash', 'zsh'
        """,
    )
    result = build_fixture_result(
        spf_doctree_root / "warning-and-manual-options",
        buildername="dummy",
        fixture_source=fixture_source,
        index_rst=index_rst,
        confoverrides={"pytest_fixture_lint_level": "warning"},
    )
    doctree = get_doctree(result, "index", post_transforms=True)

    snapshot_doctree(
        doctree,
        name="warning_and_manual_options_doctree",
        roots=(result.srcdir, result.outdir),
    )
    snapshot_warnings(
        result.warnings,
        name="warning_and_manual_options_warnings",
        roots=(result.srcdir, result.outdir),
    )


def test_autofixture_index_resolution_smoke(
    spf_doctree_root: pathlib.Path,
) -> None:
    """Fixture index placeholder resolves into a linked table after transforms."""
    index_rst = textwrap.dedent(
        """\
        Test fixtures
        =============

        .. py:module:: fixture_mod

        .. autofixture-index:: fixture_mod

        .. autofixture:: fixture_mod.my_server

        .. py:fixture:: my_client
           :deprecated: 1.5

        .. autofixture:: fixture_mod.TestServer

        .. autofixture:: fixture_mod.auto_cleanup

        .. autofixture:: fixture_mod.plain_fixture
        """,
    )
    result = build_fixture_result(
        spf_doctree_root / "autofixture-index-table",
        buildername="dummy",
        fixture_source=_AUTOFIXTURE_INDEX_SMOKE_SOURCE,
        index_rst=index_rst,
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    doctree = get_doctree(result, "index", post_transforms=True)
    table = _find_first_table(doctree)
    table_text = table.pformat()

    assert "autofixture_index_node" not in doctree.pformat()
    assert "spf-fixture-index" in table.get("classes", [])
    assert 'refid="fixture_mod.my_server"' in table_text
    assert "plain_fixture" in table_text
    assert ":fixture:" not in table_text


def test_autofixtures_directive_smoke(
    autofixtures_usage_result: SharedSphinxResult,
) -> None:
    """``autofixtures`` still expands into fixture descriptions."""
    default_doctree = get_doctree(
        autofixtures_usage_result, "index", post_transforms=True
    )
    fixture_ids = _fixture_order(default_doctree)
    assert fixture_ids == [
        "fixture_mod.my_server",
        "fixture_mod.my_client",
        "fixture_mod.renamed_fixture",
    ]


def test_short_name_fixture_reference_resolves(
    autofixtures_usage_result: SharedSphinxResult,
) -> None:
    """Short-name ``:fixture:`` references resolve after post-transforms."""
    doctree = get_doctree(autofixtures_usage_result, "index", post_transforms=True)
    text = doctree.pformat()

    assert '<reference internal="True" refid="fixture_mod.my_server"' in text
    assert ":fixture:" not in text


def test_doc_pytest_plugin_rst_snapshot(
    spf_doctree_root: pathlib.Path,
    snapshot_doctree,
) -> None:
    """Snapshot the generated RST auto-pytest-plugin page content."""
    index_rst = textwrap.dedent(
        """\
        Test fixtures
        =============

        .. auto-pytest-plugin:: fixture_mod
           :project: fixture-demo
           :package: fixture-demo
           :summary: fixture-demo ships a pytest plugin for local test setup.
           :tests-url: https://example.com/fixture-demo/tests
           :install-command: uv add --dev fixture-demo

           Use the plugin when you want isolated test resources with minimal
           conftest boilerplate.
        """,
    )
    result = build_fixture_result(
        spf_doctree_root / "auto-pytest-plugin-rst",
        buildername="dummy",
        fixture_source=_AUTOFIXTURES_SMOKE_SOURCE,
        index_rst=index_rst,
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    doctree = get_doctree(result, "index", post_transforms=True)

    snapshot_doctree(
        doctree,
        name="doc_pytest_plugin_rst",
        roots=(result.srcdir, result.outdir),
    )


def test_doc_pytest_plugin_myst_smoke(
    myst_smoke_result: SharedSphinxResult,
) -> None:
    """MyST ``auto-pytest-plugin`` keeps authored Markdown and generated sections."""
    doctree = get_doctree(myst_smoke_result, "plugin", post_transforms=True)
    doctree_text = doctree.pformat()

    assert "Recommended fixtures" in doctree_text
    assert "generated fixture docs and authored notes" in doctree_text
    assert "Fixture Summary" in doctree_text
    assert "Fixture Reference" in doctree_text
    assert "fixture_mod.my_server" in doctree_text


def test_autofixtures_directive_myst_smoke(
    myst_smoke_result: SharedSphinxResult,
) -> None:
    """MyST ``autofixtures`` expands fixture descriptions in source order."""
    doctree = get_doctree(myst_smoke_result, "autofixtures", post_transforms=True)
    doctree_text = doctree.pformat()

    assert _fixture_order(doctree) == [
        "fixture_mod.my_server",
        "fixture_mod.my_client",
        "fixture_mod.renamed_fixture",
    ]
    assert "Test fixtures" in doctree_text
    assert "fixture_mod.renamed_fixture" in doctree_text
    assert "eval-rst" not in doctree_text
    assert "::{autofixtures}" not in doctree_text


def test_lint_level_error_sets_nonzero_status(
    spf_doctree_root: pathlib.Path,
) -> None:
    """Validation errors still fail the synthetic build when lint level is error."""
    result = build_fixture_result(
        spf_doctree_root / "lint-level-error",
        buildername="dummy",
        confoverrides={"pytest_fixture_lint_level": "error"},
    )

    assert result.app.statuscode != 0
