"""Doctree- and store-level tests for sphinx_autodoc_pytest_fixtures."""

from __future__ import annotations

import textwrap
import typing as t

import pytest
from docutils import nodes
from sphinx import addnodes

from tests._snapshots import normalize_warning_text
from tests._sphinx_scenarios import get_doctree
from tests.ext.pytest_fixtures._scenario_support import (
    FIXTURE_MOD_SOURCE,
    INDEX_RST,
    build_fixture_result,
)

if t.TYPE_CHECKING:
    import pathlib

    from sphinx.domains.python import PythonDomain

pytestmark = pytest.mark.integration


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


def test_default_fixture_store_and_domain_contract(tmp_path: pathlib.Path) -> None:
    """Default synthetic fixture scenario populates domain and store indices."""
    result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    domain = t.cast("PythonDomain", result.app.env.get_domain("py"))
    objects = domain.data["objects"]

    assert (
        normalize_warning_text(
            result.warnings,
            roots=(result.srcdir, result.outdir),
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

    store = result.app.env.domaindata["sphinx_autodoc_pytest_fixtures"]
    assert store["reverse_deps"]["fixture_mod.my_server"] == [
        "fixture_mod.my_client",
        "fixture_mod.yield_server",
    ]
    assert "fixture_mod.auto_cleanup" not in store["reverse_deps"]


def test_default_fixture_post_transform_snapshot(
    tmp_path: pathlib.Path,
    snapshot_doctree,
) -> None:
    """Snapshot the transformed default fixture page contract."""
    result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    doctree = get_doctree(result, "index", post_transforms=True)

    snapshot_doctree(
        doctree,
        name="default_fixture_page",
        roots=(result.srcdir, result.outdir),
    )


def test_manual_directive_without_module_registers_unqualified_name(
    tmp_path: pathlib.Path,
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
        tmp_path,
        buildername="dummy",
        index_rst=index_rst,
        confoverrides={"pytest_fixture_lint_level": "none"},
    )

    domain = t.cast("PythonDomain", result.app.env.get_domain("py"))
    assert "bare_server" in domain.data["objects"]


def test_dependency_rendering_snapshot(
    tmp_path: pathlib.Path,
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
        tmp_path,
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
    tmp_path: pathlib.Path,
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
        tmp_path,
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


def test_autofixture_index_table_snapshot(
    tmp_path: pathlib.Path,
    snapshot_doctree,
) -> None:
    """Snapshot the generated fixture index table with badge flags."""
    fixture_source = FIXTURE_MOD_SOURCE + textwrap.dedent(
        """\

        @pytest.fixture
        def plain_fixture() -> str:
            \"\"\"A plain function-scope resource fixture.\"\"\"
            return "plain"
        """,
    )
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
        tmp_path,
        buildername="dummy",
        fixture_source=fixture_source,
        index_rst=index_rst,
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    doctree = get_doctree(result, "index", post_transforms=True)

    snapshot_doctree(
        _find_first_table(doctree),
        name="autofixture_index_table",
        roots=(result.srcdir, result.outdir),
    )


def test_autofixture_index_exclude_snapshot(
    tmp_path: pathlib.Path,
    snapshot_doctree,
) -> None:
    """Snapshot ``autofixture-index`` output after exclusions are applied."""
    index_rst = textwrap.dedent(
        """\
        Test
        ====

        .. py:module:: fixture_mod

        .. autofixture-index:: fixture_mod
           :exclude: my_client, auto_cleanup

        .. autofixture:: fixture_mod.my_server

        .. autofixture:: fixture_mod.my_client

        .. autofixture:: fixture_mod.auto_cleanup
        """,
    )
    result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        index_rst=index_rst,
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    doctree = get_doctree(result, "index", post_transforms=True)

    snapshot_doctree(
        _find_first_table(doctree),
        name="autofixture_index_exclude",
        roots=(result.srcdir, result.outdir),
    )


def test_autofixtures_directive_contract(tmp_path: pathlib.Path) -> None:
    """``autofixtures`` respects source order, alpha order, and exclusion."""
    default_result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        index_rst=textwrap.dedent(
            """\
            Test fixtures
            =============

            .. py:module:: fixture_mod

            .. autofixtures:: fixture_mod
            """,
        ),
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    default_doctree = get_doctree(default_result, "index", post_transforms=True)
    assert _fixture_order(default_doctree) == [
        "fixture_mod.my_server",
        "fixture_mod.my_client",
        "fixture_mod.home_user",
        "fixture_mod.yield_server",
        "fixture_mod.auto_cleanup",
        "fixture_mod.TestServer",
        "fixture_mod.renamed_fixture",
    ]

    alpha_result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        index_rst=textwrap.dedent(
            """\
            Test fixtures
            =============

            .. py:module:: fixture_mod

            .. autofixtures:: fixture_mod
               :order: alpha
            """,
        ),
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    alpha_doctree = get_doctree(alpha_result, "index", post_transforms=True)
    assert _fixture_order(alpha_doctree) == [
        "fixture_mod.TestServer",
        "fixture_mod.auto_cleanup",
        "fixture_mod.home_user",
        "fixture_mod.my_client",
        "fixture_mod.my_server",
        "fixture_mod.renamed_fixture",
        "fixture_mod.yield_server",
    ]

    exclude_result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        index_rst=textwrap.dedent(
            """\
            Test fixtures
            =============

            .. py:module:: fixture_mod

            .. autofixtures:: fixture_mod
               :exclude: my_client, auto_cleanup
            """,
        ),
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    exclude_doctree = get_doctree(exclude_result, "index", post_transforms=True)
    assert _fixture_order(exclude_doctree) == [
        "fixture_mod.my_server",
        "fixture_mod.home_user",
        "fixture_mod.yield_server",
        "fixture_mod.TestServer",
        "fixture_mod.renamed_fixture",
    ]

    warning_result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        index_rst=textwrap.dedent(
            """\
            Test fixtures
            =============

            .. autofixtures:: nonexistent_module_xyz_12345
            """,
        ),
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    assert "nonexistent_module_xyz_12345" in warning_result.warnings


def test_short_name_fixture_reference_resolves(tmp_path: pathlib.Path) -> None:
    """Short-name ``:fixture:`` references resolve after post-transforms."""
    result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        index_rst=INDEX_RST
        + textwrap.dedent(
            """\

            Usage
            -----

            See :fixture:`my_server` for the server fixture.
            """,
        ),
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    doctree = get_doctree(result, "index", post_transforms=True)
    text = doctree.pformat()

    assert '<reference internal="True" refid="fixture_mod.my_server"' in text
    assert ":fixture:" not in text


def test_doc_pytest_plugin_rst_snapshot(
    tmp_path: pathlib.Path,
    snapshot_doctree,
) -> None:
    """Snapshot the generated RST doc-pytest-plugin page content."""
    index_rst = textwrap.dedent(
        """\
        Test fixtures
        =============

        .. doc-pytest-plugin:: fixture_mod
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
        tmp_path,
        buildername="dummy",
        index_rst=index_rst,
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    doctree = get_doctree(result, "index", post_transforms=True)

    snapshot_doctree(
        doctree,
        name="doc_pytest_plugin_rst",
        roots=(result.srcdir, result.outdir),
    )


def test_doc_pytest_plugin_warning_contracts(tmp_path: pathlib.Path) -> None:
    """Doc plugin warnings and defaults are visible without full HTML builds."""
    no_fixtures_result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        fixture_source=textwrap.dedent(
            """\
            from __future__ import annotations

            def helper() -> str:
                return "helper"
            """,
        ),
        index_rst=textwrap.dedent(
            """\
            Test fixtures
            =============

            .. doc-pytest-plugin:: fixture_mod
               :project: fixture-demo
               :package: fixture-demo
            """,
        ),
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    no_fixtures_text = get_doctree(
        no_fixtures_result,
        "index",
        post_transforms=True,
    ).astext()
    assert "Fixture Summary" not in no_fixtures_text
    assert "Fixture Reference" not in no_fixtures_text
    assert "found no pytest fixtures" in no_fixtures_result.warnings

    generic_result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        index_rst=textwrap.dedent(
            """\
            Test fixtures
            =============

            .. doc-pytest-plugin:: fixture_mod
               :package: fixture-demo
               :tests-url: https://example.com/fixture-demo/tests

               Body prose only.
            """,
        ),
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    generic_text = get_doctree(generic_result, "index", post_transforms=True).astext()
    assert "test suite" in generic_text
    assert "fixture-demo test suite" not in generic_text
    assert "Body prose only." in generic_text

    missing_package_result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        index_rst=textwrap.dedent(
            """\
            Test fixtures
            =============

            .. doc-pytest-plugin:: fixture_mod

               No package option here.
            """,
        ),
        confoverrides={"pytest_fixture_lint_level": "none"},
    )
    assert "requires the :package: option" in missing_package_result.warnings


def test_doc_pytest_plugin_myst_snapshot(
    tmp_path: pathlib.Path,
    snapshot_doctree,
) -> None:
    """Snapshot MyST ``doc-pytest-plugin`` page output after transforms."""
    index_md = textwrap.dedent(
        """\
        # Test fixtures

        :::{doc-pytest-plugin} fixture_mod
        :project: fixture-demo
        :package: fixture-demo
        :summary: fixture-demo ships a pytest plugin for local test setup.
        :tests-url: https://example.com/fixture-demo/tests

        ## Recommended fixtures

        Use this page when you want generated fixture docs and authored notes.

        ## Bootstrapping in `conftest.py`

        ```python
        import pytest


        @pytest.fixture(autouse=True)
        def setup(my_server: str) -> None:
            pass
        ```
        :::
        """,
    )
    result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        index_rst=index_md,
        index_name="index.md",
        extensions=[
            "myst_parser",
            "sphinx.ext.autodoc",
            "sphinx_autodoc_pytest_fixtures",
        ],
        confoverrides={
            "pytest_fixture_lint_level": "none",
            "myst_enable_extensions": ["colon_fence"],
        },
    )
    doctree = get_doctree(result, "index", post_transforms=True)

    snapshot_doctree(
        doctree,
        name="doc_pytest_plugin_myst",
        roots=(result.srcdir, result.outdir),
    )


def test_autofixtures_directive_myst_snapshot(
    tmp_path: pathlib.Path,
    snapshot_doctree,
) -> None:
    """Snapshot MyST ``autofixtures`` output after transforms."""
    index_md = textwrap.dedent(
        """\
        # Test fixtures

        :::{eval-rst}
        .. py:module:: fixture_mod
        :::

        :::{autofixtures} fixture_mod
        :order: source
        :::
        """,
    )
    result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        index_rst=index_md,
        index_name="index.md",
        extensions=[
            "myst_parser",
            "sphinx.ext.autodoc",
            "sphinx_autodoc_pytest_fixtures",
        ],
        confoverrides={
            "pytest_fixture_lint_level": "none",
            "myst_enable_extensions": ["colon_fence"],
        },
    )
    doctree = get_doctree(result, "index", post_transforms=True)

    snapshot_doctree(
        doctree,
        name="autofixtures_myst",
        roots=(result.srcdir, result.outdir),
    )


def test_lint_level_error_sets_nonzero_status(tmp_path: pathlib.Path) -> None:
    """Validation errors still fail the synthetic build when lint level is error."""
    result = build_fixture_result(
        tmp_path,
        buildername="dummy",
        confoverrides={"pytest_fixture_lint_level": "error"},
    )

    assert result.app.statuscode != 0
