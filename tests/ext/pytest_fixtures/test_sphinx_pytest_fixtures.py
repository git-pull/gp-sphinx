"""Tests for sphinx_autodoc_pytest_fixtures Sphinx extension."""

from __future__ import annotations

import collections.abc  # noqa: TC003 — needed at runtime for get_type_hints()
import types
import typing as t

import pytest
from docutils import nodes
from sphinx_autodoc_badges import SAB, BadgeNode

import sphinx_autodoc_pytest_fixtures
import sphinx_autodoc_pytest_fixtures._directives as spf_directives
import sphinx_autodoc_pytest_fixtures._index as spf_index
import sphinx_autodoc_pytest_fixtures._store
from sphinx_autodoc_pytest_fixtures._models import FixtureMeta

try:
    import libtmux  # noqa: F401

    HAS_LIBTMUX = True
except ImportError:
    HAS_LIBTMUX = False


class Server:
    """Dummy class used as a realistic return-type annotation for test fixtures."""

    def kill(self) -> None:
        pass


def _make_fixture_meta(
    *,
    canonical_name: str,
    public_name: str | None = None,
    summary: str = "",
    return_display: str = "",
    scope: str = "function",
    kind: str = "resource",
    autouse: bool = False,
) -> FixtureMeta:
    """Return a typed ``FixtureMeta`` for helper-level index tests."""
    resolved_public_name = (
        public_name if public_name is not None else canonical_name.rsplit(".", 1)[-1]
    )
    return FixtureMeta(
        docname="index",
        canonical_name=canonical_name,
        public_name=resolved_public_name,
        source_name=resolved_public_name,
        scope=scope,
        autouse=autouse,
        kind=kind,
        return_display=return_display,
        deps=(),
        param_reprs=(),
        has_teardown=False,
        is_async=False,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# _is_pytest_fixture
# ---------------------------------------------------------------------------


def test_is_pytest_fixture_positive() -> None:
    """_is_pytest_fixture returns True for decorated fixtures."""

    @pytest.fixture(scope="session")
    def my_fixture(tmp_path_factory: pytest.TempPathFactory) -> str:
        return "hello"

    assert sphinx_autodoc_pytest_fixtures._is_pytest_fixture(my_fixture)


def test_is_pytest_fixture_negative() -> None:
    """_is_pytest_fixture returns False for plain functions."""

    def not_a_fixture() -> str:
        return "hello"

    assert not sphinx_autodoc_pytest_fixtures._is_pytest_fixture(not_a_fixture)


# ---------------------------------------------------------------------------
# autofixtures and auto-pytest-plugin helper generation
# ---------------------------------------------------------------------------


def test_build_autofixtures_directive_text_preserves_source_order() -> None:
    """Generated ``autofixtures`` text keeps discovery order by default."""
    entries: list[tuple[str, str, t.Any]] = [
        ("z_server", "z_server", object()),
        ("a_client", "a_client", object()),
    ]

    rendered = spf_directives._build_autofixtures_directive_text(
        "fixture_mod",
        entries,
    )

    assert rendered.splitlines() == [
        ".. autofixture:: fixture_mod.z_server",
        "",
        ".. autofixture:: fixture_mod.a_client",
    ]


def test_build_autofixtures_directive_text_alpha_sort_and_no_index() -> None:
    """Alpha ordering and ``:no-index:`` are encoded without Sphinx parsing."""
    entries: list[tuple[str, str, t.Any]] = [
        ("z_server", "z_server", object()),
        ("a_client", "a_client", object()),
    ]

    rendered = spf_directives._build_autofixtures_directive_text(
        "fixture_mod",
        entries,
        order="alpha",
        no_index=True,
    )

    assert rendered.splitlines() == [
        ".. autofixture:: fixture_mod.a_client",
        "   :no-index:",
        "",
        ".. autofixture:: fixture_mod.z_server",
        "   :no-index:",
    ]


def test_build_autofixtures_directive_text_wraps_eval_rst_for_myst() -> None:
    """Native MyST invocation wraps generated RST in an ``eval-rst`` fence."""
    entries: list[tuple[str, str, t.Any]] = [("server", "server", object())]

    rendered = spf_directives._build_autofixtures_directive_text(
        "fixture_mod",
        entries,
        wrap_eval_rst=True,
    )

    assert rendered.startswith("```{eval-rst}\n")
    assert ".. autofixture:: fixture_mod.server" in rendered
    assert rendered.endswith("\n```")


def test_build_doc_pytest_plugin_intro_nodes_include_install_and_link() -> None:
    """The generated intro includes summary, install block, note, and tests URL."""
    intro_nodes = spf_directives._build_doc_pytest_plugin_intro_nodes(
        project="fixture-demo",
        summary="fixture-demo ships a pytest plugin.",
        install_command="uv add --dev fixture-demo",
        tests_url="https://example.com/tests",
    )

    assert [type(node) for node in intro_nodes] == [
        nodes.paragraph,
        nodes.rubric,
        nodes.literal_block,
        nodes.note,
        nodes.paragraph,
    ]
    assert intro_nodes[0].astext() == "fixture-demo ships a pytest plugin."
    assert intro_nodes[1].astext() == "Install"
    assert intro_nodes[2].astext() == "$ uv add --dev fixture-demo"
    assert "pytest11" in intro_nodes[3].astext()
    assert "fixture-demo test suite" in intro_nodes[4].astext()


def test_build_doc_pytest_plugin_fixture_section_scaffold_sets_module() -> None:
    """Fixture-section scaffold carries the target module on the placeholder."""
    scaffold = spf_directives._build_doc_pytest_plugin_fixture_section_scaffold(
        "fixture_mod",
    )

    assert [type(node) for node in scaffold] == [
        nodes.rubric,
        spf_directives.autofixture_index_node,
        nodes.rubric,
    ]
    assert scaffold[0].astext() == "Fixture Summary"
    assert scaffold[1]["module"] == "fixture_mod"
    assert scaffold[1]["exclude"] == set()
    assert scaffold[2].astext() == "Fixture Reference"


def test_compose_doc_pytest_plugin_nodes_preserves_display_order() -> None:
    """Intro, authored body, and fixture section nodes stay in display order."""
    intro_nodes = [nodes.paragraph("", "intro")]
    body_nodes = [nodes.paragraph("", "body")]
    fixture_section_nodes = [nodes.paragraph("", "fixtures")]

    composed = spf_directives._compose_doc_pytest_plugin_nodes(
        intro_nodes=intro_nodes,
        body_nodes=body_nodes,
        fixture_section_nodes=fixture_section_nodes,
    )

    assert [node.astext() for node in composed] == ["intro", "body", "fixtures"]


def test_select_fixture_index_fixtures_filters_module_and_exclude() -> None:
    """Fixture-index row selection stays a pure metadata filter."""
    store = sphinx_autodoc_pytest_fixtures._store._make_empty_store()
    store["fixtures"] = {
        "fixture_mod.alpha": _make_fixture_meta(canonical_name="fixture_mod.alpha"),
        "fixture_mod.beta": _make_fixture_meta(canonical_name="fixture_mod.beta"),
        "other_mod.gamma": _make_fixture_meta(canonical_name="other_mod.gamma"),
    }

    selected = spf_index._select_fixture_index_fixtures(
        store,
        "fixture_mod",
        {"beta"},
    )

    assert [meta.canonical_name for meta in selected] == ["fixture_mod.alpha"]


def test_build_fixture_index_table_structure_populates_plain_shell() -> None:
    """Fixture-index shell building does not need a Sphinx app."""
    fixtures = [
        _make_fixture_meta(
            canonical_name="fixture_mod.my_server",
            return_display="Server",
            summary="Session-scoped test server.",
            scope="session",
        ),
        _make_fixture_meta(
            canonical_name="fixture_mod.auto_cleanup",
            summary="Runs automatically.",
            autouse=True,
        ),
    ]

    table, tbody = spf_index._build_fixture_index_table_structure(fixtures)

    assert isinstance(table, nodes.table)
    assert isinstance(tbody, nodes.tbody)
    assert len(tbody.children) == 2
    first_row = t.cast(nodes.row, tbody.children[0])
    assert len(first_row.children) == 4
    first_name_entry = t.cast(nodes.entry, first_row.children[0])
    first_flags_entry = t.cast(nodes.entry, first_row.children[1])
    first_return_entry = t.cast(nodes.entry, first_row.children[2])
    first_desc_entry = t.cast(nodes.entry, first_row.children[3])
    assert "my_server" in first_name_entry.astext()
    assert "session" in first_flags_entry.astext()
    assert "Server" in first_return_entry.astext()
    assert "Session-scoped test server." in first_desc_entry.astext()


def test_resolve_fixture_index_uses_shared_annotation_paragraph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fixture index resolution delegates return types to shared helpers."""
    seen: dict[str, str] = {}
    store = sphinx_autodoc_pytest_fixtures._store._make_empty_store()
    store["fixtures"] = {
        "fixture_mod.server": _make_fixture_meta(
            canonical_name="fixture_mod.server",
            return_display="fixture_mod.Server",
            summary="Server fixture.",
        )
    }

    def _fake_build_resolved_annotation_paragraph(
        annotation: t.Any,
        app: t.Any,
        docname: str,
        *,
        strip_none: bool = False,
        collapse_literal: bool = False,
        module_name: str | None = None,
        aliases: dict[str, str] | None = None,
        qualify_unresolved: bool = False,
    ) -> nodes.paragraph:
        del (
            app,
            docname,
            strip_none,
            collapse_literal,
            module_name,
            aliases,
            qualify_unresolved,
        )
        seen["annotation"] = t.cast(str, annotation)
        return nodes.paragraph("", f"shared::{annotation}")

    monkeypatch.setattr(
        spf_index,
        "build_resolved_annotation_paragraph",
        _fake_build_resolved_annotation_paragraph,
    )

    placeholder = spf_directives.autofixture_index_node(
        module="fixture_mod",
        exclude=set(),
    )
    container = nodes.section("", placeholder)
    app = types.SimpleNamespace(env=types.SimpleNamespace(), builder=object())
    py_domain = types.SimpleNamespace(objects={})

    spf_index._resolve_fixture_index(
        placeholder,
        store,
        py_domain,
        app,
        "index",
    )

    assert seen["annotation"] == "fixture_mod.Server"
    rendered_section = t.cast(nodes.Element, container.children[0])
    assert rendered_section.get("name") == "api-summary"
    assert "shared::fixture_mod.Server" in rendered_section.astext()


# ---------------------------------------------------------------------------
# _get_user_deps
# ---------------------------------------------------------------------------


def test_user_deps_filters_pytest_hidden() -> None:
    """_get_user_deps excludes fixtures in PYTEST_HIDDEN (low-value noise).

    Fixtures in PYTEST_BUILTIN_LINKS (request, monkeypatch, etc.) are NOT
    filtered by _get_user_deps — they are rendered with external hyperlinks
    by transform_content instead.
    """

    @pytest.fixture
    def my_fixture(
        pytestconfig: pytest.Config,
        monkeypatch: pytest.MonkeyPatch,
        server: t.Any,
    ) -> str:
        return "hello"

    deps = sphinx_autodoc_pytest_fixtures._get_user_deps(my_fixture)
    names = [name for name, _ in deps]
    # pytestconfig is in PYTEST_HIDDEN → filtered
    assert "pytestconfig" not in names
    # monkeypatch is in PYTEST_BUILTIN_LINKS (not PYTEST_HIDDEN) → appears
    assert "monkeypatch" in names
    # project fixture → appears
    assert "server" in names


def test_user_deps_empty_for_only_hidden_params() -> None:
    """_get_user_deps returns empty list when all params are in PYTEST_HIDDEN."""

    @pytest.fixture
    def my_fixture(pytestconfig: pytest.Config) -> str:
        return "hello"

    assert sphinx_autodoc_pytest_fixtures._get_user_deps(my_fixture) == []


# ---------------------------------------------------------------------------
# _get_return_annotation — including Generator/yield unwrapping
# ---------------------------------------------------------------------------


def test_get_return_annotation_resolved() -> None:
    """_get_return_annotation returns the resolved return type."""

    @pytest.fixture
    def my_fixture() -> str:
        return "hello"

    ann = sphinx_autodoc_pytest_fixtures._get_return_annotation(my_fixture)
    assert ann is str


def test_get_return_annotation_forward_ref_fallback() -> None:
    """_get_return_annotation falls back gracefully on unresolvable forward refs."""

    @pytest.fixture
    def my_fixture() -> UnresolvableForwardRef:  # type: ignore[name-defined]  # noqa: F821
        return None

    # Should not raise; returns the annotation string or Parameter.empty
    ann = sphinx_autodoc_pytest_fixtures._get_return_annotation(my_fixture)
    assert ann is not None


def test_get_return_annotation_unwraps_generator() -> None:
    """_get_return_annotation extracts yield type from Generator[T, None, None]."""

    @pytest.fixture
    def server_fixture() -> collections.abc.Generator[Server, None, None]:
        srv = Server()
        yield srv
        srv.kill()

    ann = sphinx_autodoc_pytest_fixtures._get_return_annotation(server_fixture)
    assert ann is Server


def test_get_return_annotation_unwraps_iterator() -> None:
    """_get_return_annotation extracts yield type from Iterator[T]."""

    @pytest.fixture
    def server_fixture() -> collections.abc.Iterator[Server]:
        return Server()

    ann = sphinx_autodoc_pytest_fixtures._get_return_annotation(server_fixture)
    assert ann is Server


# ---------------------------------------------------------------------------
# _is_factory
# ---------------------------------------------------------------------------


def test_factory_detection_from_type_annotation() -> None:
    """_is_factory returns True for type[X] return annotation."""

    @pytest.fixture
    def test_factory(request: pytest.FixtureRequest) -> type[Server]:
        return Server

    assert sphinx_autodoc_pytest_fixtures._is_factory(test_factory)


def test_factory_detection_from_callable_annotation() -> None:
    """_is_factory returns True for Callable return annotation."""

    @pytest.fixture
    def make_thing() -> collections.abc.Callable[[], str]:
        return lambda: "x"

    assert sphinx_autodoc_pytest_fixtures._is_factory(make_thing)


def test_factory_detection_from_name_convention() -> None:
    """_is_factory returns False for unannotated (t.Any) fixtures; no name heuristic."""

    @pytest.fixture
    def CapitalFactory() -> t.Any:
        return lambda: None

    assert not sphinx_autodoc_pytest_fixtures._is_factory(CapitalFactory)


def test_is_factory_camelcase_unannotated_defaults_to_resource() -> None:
    """Unannotated CamelCase fixture must NOT be silently classified as factory."""

    @pytest.fixture
    def Session() -> t.Any:
        return "string value"

    assert not sphinx_autodoc_pytest_fixtures._is_factory(Session)


def test_factory_detection_negative() -> None:
    """_is_factory returns False for plain resource fixtures."""

    @pytest.fixture
    def plain_fixture() -> str:
        return "hello"

    assert not sphinx_autodoc_pytest_fixtures._is_factory(plain_fixture)


# ---------------------------------------------------------------------------
# format_name (via getattr pattern used in FixtureDocumenter.format_name)
# ---------------------------------------------------------------------------


def test_format_name_uses_function_name_when_not_renamed() -> None:
    """format_name returns the function name when no name alias is set."""

    @pytest.fixture
    def server_fixture() -> str:
        return "hello"

    fixture_name = (
        getattr(
            server_fixture,
            "name",
            None,
        )
        or sphinx_autodoc_pytest_fixtures._get_fixture_fn(server_fixture).__name__
    )
    assert fixture_name == "server_fixture"


def test_format_name_honours_fixture_name_alias() -> None:
    """format_name returns the alias when @pytest.fixture(name=...) is used."""

    @pytest.fixture(name="server")
    def _server_fixture() -> str:
        return "hello"

    fixture_name = (
        getattr(
            _server_fixture,
            "name",
            None,
        )
        or sphinx_autodoc_pytest_fixtures._get_fixture_fn(_server_fixture).__name__
    )
    assert fixture_name == "server"


# ---------------------------------------------------------------------------
# setup()
# ---------------------------------------------------------------------------


def test_setup_return_value() -> None:
    """setup() returns correct extension metadata."""
    connections: list[tuple[str, t.Any]] = []
    setup_extensions: list[str] = []

    app = types.SimpleNamespace(
        setup_extension=setup_extensions.append,
        add_config_value=lambda name, default, rebuild, **kw: None,
        add_crossref_type=lambda *a, **kw: None,
        add_directive_to_domain=lambda d, n, cls: None,
        add_role_to_domain=lambda d, n, role: None,
        add_autodocumenter=lambda cls: None,
        add_directive=lambda name, cls: None,
        add_node=lambda *a, **kw: None,
        add_css_file=lambda *a, **kw: None,
        connect=lambda event, handler: connections.append((event, handler)),
    )

    result = sphinx_autodoc_pytest_fixtures.setup(app)
    assert result["version"] == "1.0"
    assert result["parallel_read_safe"] is True
    assert result["parallel_write_safe"] is True
    assert setup_extensions == [
        "sphinx.ext.autodoc",
        "sphinx_autodoc_badges",
        "sphinx_autodoc_layout",
        "sphinx_autodoc_typehints_gp",
    ]


def test_setup_event_connections() -> None:
    """setup() connects required event handlers."""
    connections: list[tuple[str, t.Any]] = []

    app = types.SimpleNamespace(
        setup_extension=lambda ext: None,
        add_config_value=lambda name, default, rebuild, **kw: None,
        add_crossref_type=lambda *a, **kw: None,
        add_directive_to_domain=lambda d, n, cls: None,
        add_role_to_domain=lambda d, n, role: None,
        add_autodocumenter=lambda cls: None,
        add_directive=lambda name, cls: None,
        add_node=lambda *a, **kw: None,
        add_css_file=lambda *a, **kw: None,
        connect=lambda event, handler: connections.append((event, handler)),
    )

    sphinx_autodoc_pytest_fixtures.setup(app)
    event_names = [e for e, _ in connections]
    assert "missing-reference" in event_names
    assert "doctree-resolved" in event_names
    assert "env-purge-doc" in event_names
    assert "env-merge-info" in event_names
    assert "env-updated" in event_names

    handlers = dict(connections)
    assert (
        handlers["missing-reference"]
        is sphinx_autodoc_pytest_fixtures._on_missing_reference
    )


def test_setup_registers_autodocumenter() -> None:
    """setup() registers FixtureDocumenter."""
    registered: list[t.Any] = []

    app = types.SimpleNamespace(
        setup_extension=lambda ext: None,
        add_config_value=lambda name, default, rebuild, **kw: None,
        add_crossref_type=lambda *a, **kw: None,
        add_directive_to_domain=lambda d, n, cls: None,
        add_role_to_domain=lambda d, n, role: None,
        add_autodocumenter=registered.append,
        add_directive=lambda name, cls: None,
        add_node=lambda *a, **kw: None,
        add_css_file=lambda *a, **kw: None,
        connect=lambda event, handler: None,
    )

    sphinx_autodoc_pytest_fixtures.setup(app)
    assert sphinx_autodoc_pytest_fixtures.FixtureDocumenter in registered


# ---------------------------------------------------------------------------
# _get_fixture_marker — scope normalisation (Commit 1)
# ---------------------------------------------------------------------------


def test_get_fixture_marker_scope_is_str_for_session() -> None:
    """_get_fixture_marker always returns str scope, never enum or None."""

    @pytest.fixture(scope="session")
    def my_fixture() -> str:
        return "hello"

    marker = sphinx_autodoc_pytest_fixtures._get_fixture_marker(my_fixture)
    assert isinstance(marker.scope, str)
    assert marker.scope == "session"


def test_get_fixture_marker_function_scope_is_str() -> None:
    """Function-scope (default) fixture returns 'function', not None."""

    @pytest.fixture
    def fn_fixture() -> str:
        return "x"

    marker = sphinx_autodoc_pytest_fixtures._get_fixture_marker(fn_fixture)
    assert isinstance(marker.scope, str)
    assert marker.scope == "function"


# ---------------------------------------------------------------------------
# _iter_injectable_params — variadic filter (Commit 1)
# ---------------------------------------------------------------------------


def test_iter_injectable_params_skips_kwargs() -> None:
    """_iter_injectable_params skips *args and **kwargs."""

    @pytest.fixture
    def fx(server: t.Any, *args: t.Any, **kwargs: t.Any) -> None:
        pass

    names = [n for n, _ in sphinx_autodoc_pytest_fixtures._iter_injectable_params(fx)]
    assert names == ["server"]
    assert "args" not in names
    assert "kwargs" not in names


def test_iter_injectable_params_keeps_keyword_only() -> None:
    """_iter_injectable_params includes KEYWORD_ONLY params — pytest can inject them."""

    @pytest.fixture
    def fx(*, server: t.Any) -> None:
        pass

    names = [n for n, _ in sphinx_autodoc_pytest_fixtures._iter_injectable_params(fx)]
    assert "server" in names


def test_iter_injectable_params_skips_positional_only() -> None:
    """_iter_injectable_params skips POSITIONAL_ONLY params (before /).

    Positional-only parameters cannot be injected by name, so they are
    correctly excluded from the fixture dependency list.
    """
    import textwrap

    code = textwrap.dedent("""
        import pytest
        import typing as t

        @pytest.fixture
        def fx(server: t.Any, /, *, session: t.Any) -> None:
            pass
    """)
    ns: dict[str, t.Any] = {}
    exec(compile(code, "<test>", "exec"), ns)
    names = [
        n for n, _ in sphinx_autodoc_pytest_fixtures._iter_injectable_params(ns["fx"])
    ]
    assert names == ["session"]
    assert "server" not in names


# ---------------------------------------------------------------------------
# _build_badge_group_node — portable inline badge nodes (Commit 4)
# ---------------------------------------------------------------------------


def test_build_badge_group_node_fixture_always_present() -> None:
    """_build_badge_group_node always includes a FIXTURE badge child."""
    node = sphinx_autodoc_pytest_fixtures._build_badge_group_node(
        "function", "resource", False
    )
    texts = [child.astext() for child in node.children]
    assert "fixture" in texts


def test_build_badge_group_node_no_scope_for_function() -> None:
    """Function-scope produces no scope badge (absence = function-scope)."""
    node = sphinx_autodoc_pytest_fixtures._build_badge_group_node(
        "function", "resource", False
    )
    classes_all = [
        c
        for child in node.children
        if hasattr(child, "get")
        for c in child.get("classes", [])
    ]
    assert SAB.BADGE_SCOPE not in classes_all


def test_build_badge_group_node_session_scope_badge() -> None:
    """Session-scope produces a scope badge with class spf-scope-session."""
    node = sphinx_autodoc_pytest_fixtures._build_badge_group_node(
        "session", "resource", False
    )
    classes_all = [
        c
        for child in node.children
        if hasattr(child, "get")
        for c in child.get("classes", [])
    ]
    assert SAB.scope("session") in classes_all


def test_build_badge_group_node_override_kind() -> None:
    """override_hook produces a badge with class spf-override."""
    node = sphinx_autodoc_pytest_fixtures._build_badge_group_node(
        "function", "override_hook", False
    )
    texts = [child.astext() for child in node.children]
    classes_all = [
        c
        for child in node.children
        if hasattr(child, "get")
        for c in child.get("classes", [])
    ]
    assert "override" in texts
    assert SAB.STATE_OVERRIDE in classes_all


def test_build_badge_group_node_autouse_replaces_kind() -> None:
    """autouse=True shows AUTO badge with spf-autouse class, no kind badge."""
    node = sphinx_autodoc_pytest_fixtures._build_badge_group_node(
        "function", "resource", True
    )
    texts = [child.astext() for child in node.children]
    classes_all = [
        c
        for child in node.children
        if hasattr(child, "get")
        for c in child.get("classes", [])
    ]
    assert "auto" in texts
    assert SAB.STATE_AUTOUSE in classes_all
    assert SAB.BADGE_KIND not in classes_all


def test_build_badge_group_node_factory_session() -> None:
    """Factory + session scope produces both scope and factory badges."""
    node = sphinx_autodoc_pytest_fixtures._build_badge_group_node(
        "session", "factory", False
    )
    texts = [child.astext() for child in node.children]
    classes_all = [
        c
        for child in node.children
        if hasattr(child, "get")
        for c in child.get("classes", [])
    ]
    assert "factory" in texts
    assert SAB.STATE_FACTORY in classes_all
    assert SAB.scope("session") in classes_all


def test_build_badge_group_node_has_tabindex() -> None:
    """All badge abbreviation nodes have tabindex='0' for touch accessibility."""

    node = sphinx_autodoc_pytest_fixtures._build_badge_group_node(
        "session", "factory", True
    )
    abbreviations = [child for child in node.children if isinstance(child, BadgeNode)]
    assert len(abbreviations) > 0
    for abbr in abbreviations:
        assert abbr.get("tabindex") == "0", (
            f"Badge {abbr.astext()!r} missing tabindex='0'"
        )


# ---------------------------------------------------------------------------
# _get_spf_store — store version guard
# ---------------------------------------------------------------------------


def test_store_version_guard_resets_stale() -> None:
    """_get_spf_store resets a store with an outdated _store_version."""
    env = types.SimpleNamespace(
        domaindata={
            "sphinx_autodoc_pytest_fixtures": {
                "fixtures": {"old.fixture": "stale"},
                "public_to_canon": {"old": "old.fixture"},
                "reverse_deps": {},
                "_store_version": 1,
            }
        }
    )
    store = sphinx_autodoc_pytest_fixtures._get_spf_store(env)
    assert store["fixtures"] == {}
    assert store["public_to_canon"] == {}
    assert store["_store_version"] == sphinx_autodoc_pytest_fixtures._STORE_VERSION


def test_store_version_guard_preserves_current() -> None:
    """_get_spf_store preserves a store with the current _store_version."""
    sentinel_meta = types.SimpleNamespace(docname="api", public_name="srv")
    env = types.SimpleNamespace(
        domaindata={
            "sphinx_autodoc_pytest_fixtures": {
                "fixtures": {"mod.srv": sentinel_meta},
                "public_to_canon": {"srv": "mod.srv"},
                "reverse_deps": {},
                "_store_version": sphinx_autodoc_pytest_fixtures._STORE_VERSION,
            }
        }
    )
    store = sphinx_autodoc_pytest_fixtures._get_spf_store(env)
    assert store["fixtures"]["mod.srv"] is sentinel_meta


# ---------------------------------------------------------------------------
# public_to_canon registration logic
# ---------------------------------------------------------------------------


def test_public_to_canon_first_registration() -> None:
    """First registration stores canonical name for a public name."""
    env = types.SimpleNamespace(domaindata={})
    store = sphinx_autodoc_pytest_fixtures._get_spf_store(env)

    store["public_to_canon"]["server"] = "mod_a.server"
    assert store["public_to_canon"]["server"] == "mod_a.server"


def test_public_to_canon_ambiguous() -> None:
    """Two fixtures with the same public name mark the mapping as None."""
    env = types.SimpleNamespace(domaindata={})
    store = sphinx_autodoc_pytest_fixtures._get_spf_store(env)

    # Simulate what _register_fixture_meta does (corrected logic):
    public_name = "server"

    # First registration
    if public_name not in store["public_to_canon"]:
        store["public_to_canon"][public_name] = "mod_a.server"
    elif store["public_to_canon"][public_name] != "mod_a.server":
        store["public_to_canon"][public_name] = None

    # Second registration with different canonical name
    if public_name not in store["public_to_canon"]:
        store["public_to_canon"][public_name] = "mod_b.server"
    elif store["public_to_canon"][public_name] != "mod_b.server":
        store["public_to_canon"][public_name] = None

    assert store["public_to_canon"]["server"] is None


def test_public_to_canon_idempotent() -> None:
    """Registering the same fixture twice preserves the canonical name."""
    env = types.SimpleNamespace(domaindata={})
    store = sphinx_autodoc_pytest_fixtures._get_spf_store(env)

    public_name = "server"

    # First registration
    if public_name not in store["public_to_canon"]:
        store["public_to_canon"][public_name] = "mod.server"
    elif store["public_to_canon"][public_name] != "mod.server":
        store["public_to_canon"][public_name] = None

    # Same fixture registered again
    if public_name not in store["public_to_canon"]:
        store["public_to_canon"][public_name] = "mod.server"
    elif store["public_to_canon"][public_name] != "mod.server":
        store["public_to_canon"][public_name] = None

    assert store["public_to_canon"]["server"] == "mod.server"


# ---------------------------------------------------------------------------
# _finalize_store — store finalization
# ---------------------------------------------------------------------------


def _make_meta(
    canonical: str,
    public: str,
    deps: tuple[sphinx_autodoc_pytest_fixtures.FixtureDep, ...] = (),
    docname: str = "api",
) -> sphinx_autodoc_pytest_fixtures.FixtureMeta:
    """Build a minimal FixtureMeta for unit tests."""
    return sphinx_autodoc_pytest_fixtures.FixtureMeta(
        docname=docname,
        canonical_name=canonical,
        public_name=public,
        source_name=public,
        scope="function",
        autouse=False,
        kind="resource",
        return_display="str",
        deps=deps,
        param_reprs=(),
        has_teardown=False,
        is_async=False,
        summary="Test fixture.",
    )


def test_finalize_store_forward_reference() -> None:
    """_finalize_store resolves forward-reference dep targets."""
    env = types.SimpleNamespace(domaindata={})
    store = sphinx_autodoc_pytest_fixtures._get_spf_store(env)

    # consumer registered before provider → dep.target is None
    consumer_dep = sphinx_autodoc_pytest_fixtures.FixtureDep(
        display_name="provider", kind="fixture", target=None
    )
    store["fixtures"]["mod.consumer"] = _make_meta(
        "mod.consumer", "consumer", deps=(consumer_dep,)
    )
    store["fixtures"]["mod.provider"] = _make_meta("mod.provider", "provider")

    sphinx_autodoc_pytest_fixtures._finalize_store(store)

    resolved_dep = store["fixtures"]["mod.consumer"].deps[0]
    assert resolved_dep.target == "mod.provider"


def test_finalize_store_empty_store() -> None:
    """_finalize_store on an empty store completes without error."""
    env = types.SimpleNamespace(domaindata={})
    store = sphinx_autodoc_pytest_fixtures._get_spf_store(env)
    sphinx_autodoc_pytest_fixtures._finalize_store(store)
    assert store["fixtures"] == {}
    assert store["public_to_canon"] == {}
    assert store["reverse_deps"] == {}


def test_finalize_store_self_dependency() -> None:
    """_finalize_store skips self-edges in reverse_deps."""
    env = types.SimpleNamespace(domaindata={})
    store = sphinx_autodoc_pytest_fixtures._get_spf_store(env)

    self_dep = sphinx_autodoc_pytest_fixtures.FixtureDep(
        display_name="self_ref", kind="fixture", target=None
    )
    store["fixtures"]["mod.self_ref"] = _make_meta(
        "mod.self_ref", "self_ref", deps=(self_dep,)
    )

    sphinx_autodoc_pytest_fixtures._finalize_store(store)

    # dep.target resolves to itself, but reverse_deps should not contain self-edge
    assert "mod.self_ref" not in store["reverse_deps"].get("mod.self_ref", [])


def test_finalize_store_ambiguous_public_name() -> None:
    """_finalize_store marks ambiguous public names as None in public_to_canon."""
    env = types.SimpleNamespace(domaindata={})
    store = sphinx_autodoc_pytest_fixtures._get_spf_store(env)

    store["fixtures"]["mod_a.server"] = _make_meta("mod_a.server", "server")
    store["fixtures"]["mod_b.server"] = _make_meta("mod_b.server", "server")

    sphinx_autodoc_pytest_fixtures._finalize_store(store)

    assert store["public_to_canon"]["server"] is None


def test_finalize_store_reverse_deps() -> None:
    """_finalize_store populates reverse_deps from fixture deps."""
    env = types.SimpleNamespace(domaindata={})
    store = sphinx_autodoc_pytest_fixtures._get_spf_store(env)

    dep_on_server = sphinx_autodoc_pytest_fixtures.FixtureDep(
        display_name="server", kind="fixture", target="mod.server"
    )
    store["fixtures"]["mod.server"] = _make_meta("mod.server", "server")
    store["fixtures"]["mod.client"] = _make_meta(
        "mod.client", "client", deps=(dep_on_server,)
    )

    sphinx_autodoc_pytest_fixtures._finalize_store(store)

    assert "mod.client" in store["reverse_deps"]["mod.server"]


def test_finalize_store_parallel_merge() -> None:
    """_finalize_store resolves deps after parallel worker merge."""
    # Simulate primary env with consumer, sub-env with provider
    primary_env = types.SimpleNamespace(domaindata={})
    primary_store = sphinx_autodoc_pytest_fixtures._get_spf_store(primary_env)

    consumer_dep = sphinx_autodoc_pytest_fixtures.FixtureDep(
        display_name="provider", kind="fixture", target=None
    )
    primary_store["fixtures"]["mod.consumer"] = _make_meta(
        "mod.consumer", "consumer", deps=(consumer_dep,)
    )

    # Simulate sub-env merge
    sub_env = types.SimpleNamespace(domaindata={})
    sub_store = sphinx_autodoc_pytest_fixtures._get_spf_store(sub_env)
    sub_store["fixtures"]["mod.provider"] = _make_meta(
        "mod.provider", "provider", docname="other"
    )

    # Merge (what _on_env_merge_info does)
    primary_store["fixtures"].update(sub_store["fixtures"])

    # Finalize
    sphinx_autodoc_pytest_fixtures._finalize_store(primary_store)

    resolved_dep = primary_store["fixtures"]["mod.consumer"].deps[0]
    assert resolved_dep.target == "mod.provider"
    assert "mod.consumer" in primary_store["reverse_deps"]["mod.provider"]


def test_finalize_store_stale_target_after_purge() -> None:
    """_finalize_store clears stale dep targets after provider is purged."""
    env = types.SimpleNamespace(domaindata={})
    store = sphinx_autodoc_pytest_fixtures._get_spf_store(env)

    dep_on_provider = sphinx_autodoc_pytest_fixtures.FixtureDep(
        display_name="provider", kind="fixture", target="mod.provider"
    )
    store["fixtures"]["mod.consumer"] = _make_meta(
        "mod.consumer", "consumer", deps=(dep_on_provider,)
    )
    store["fixtures"]["mod.provider"] = _make_meta("mod.provider", "provider")

    # Simulate purge of provider
    del store["fixtures"]["mod.provider"]

    sphinx_autodoc_pytest_fixtures._finalize_store(store)

    resolved_dep = store["fixtures"]["mod.consumer"].deps[0]
    assert resolved_dep.target is None
    assert "mod.provider" not in store["reverse_deps"]


# ---------------------------------------------------------------------------
# Badge group text separators (Commit 4)
# ---------------------------------------------------------------------------


def test_badge_group_node_has_text_separators() -> None:
    """Badge group nodes have Text(' ') separators between badge children."""
    from docutils import nodes as docnodes

    node = sphinx_autodoc_pytest_fixtures._build_badge_group_node(
        "session", "factory", False
    )
    # Should have: scope badge, Text(" "), factory badge, Text(" "), FIXTURE badge
    text_nodes = [child for child in node.children if isinstance(child, docnodes.Text)]
    assert len(text_nodes) >= 2, f"Expected >=2 Text separators, got {len(text_nodes)}"
    for t_node in text_nodes:
        assert t_node.astext() == " "


# ---------------------------------------------------------------------------
# FixtureKind validation (Commit 4)
# ---------------------------------------------------------------------------


def test_infer_kind_custom_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Unknown :kind: values produce a warning during registration."""
    import logging

    env = types.SimpleNamespace(
        domaindata={},
        app=types.SimpleNamespace(
            config=types.SimpleNamespace(
                pytest_fixture_hidden_dependencies=frozenset(),
                pytest_fixture_builtin_links={},
                pytest_fixture_external_links={},
            ),
        ),
    )

    @pytest.fixture
    def my_fixture() -> str:
        """Return a test value."""
        return "hello"

    with caplog.at_level(logging.WARNING, logger="sphinx_autodoc_pytest_fixtures"):
        sphinx_autodoc_pytest_fixtures._register_fixture_meta(
            env=env,
            docname="api",
            obj=my_fixture,
            public_name="my_fixture",
            source_name="my_fixture",
            modname="mod",
            kind="custom_weird_kind",
            app=env.app,
        )

    assert any("custom_weird_kind" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _classify_deps
# ---------------------------------------------------------------------------


def test_classify_deps_project_fixture() -> None:
    """Non-builtin, non-hidden dep is classified as a project fixture."""

    @pytest.fixture
    def my_fixture(server: t.Any) -> str:
        return "hello"

    project, builtin, hidden = sphinx_autodoc_pytest_fixtures._classify_deps(
        my_fixture, None
    )
    assert "server" in project
    assert "server" not in builtin
    assert "server" not in hidden


def test_classify_deps_hidden_fixture() -> None:
    """Fixture depending on pytestconfig has it classified as hidden."""

    @pytest.fixture
    def my_fixture(pytestconfig: t.Any) -> str:
        return "hello"

    project, _builtin, hidden = sphinx_autodoc_pytest_fixtures._classify_deps(
        my_fixture, None
    )
    assert "pytestconfig" in hidden
    assert "pytestconfig" not in project


# ---------------------------------------------------------------------------
# _has_authored_example
# ---------------------------------------------------------------------------


def test_has_authored_example_with_rubric() -> None:
    """Authored Example rubric suppresses auto-generated snippets."""

    content = nodes.container()
    content += nodes.paragraph("", "Some intro text.")
    content += nodes.rubric("", "Example")
    content += nodes.literal_block("", "def test(): pass")
    assert sphinx_autodoc_pytest_fixtures._has_authored_example(content)


def test_has_authored_example_with_doctest() -> None:
    """Doctest blocks count as authored examples."""

    content = nodes.container()
    content += nodes.doctest_block("", ">>> 1 + 1\n2")
    assert sphinx_autodoc_pytest_fixtures._has_authored_example(content)


def test_has_authored_example_without() -> None:
    """No authored examples — auto-snippet should still be generated."""

    content = nodes.container()
    content += nodes.paragraph("", "Just a description.")
    assert not sphinx_autodoc_pytest_fixtures._has_authored_example(content)


def test_has_authored_example_nested_not_detected() -> None:
    """Nested rubrics inside admonitions are not detected (non-recursive)."""

    content = nodes.container()
    admonition = nodes.note()
    admonition += nodes.rubric("", "Example")
    content += admonition
    assert not sphinx_autodoc_pytest_fixtures._has_authored_example(content)


# ---------------------------------------------------------------------------
# _build_usage_snippet
# ---------------------------------------------------------------------------


def test_build_usage_snippet_resource_returns_none() -> None:
    """Resource fixtures return None (generic snippet suppressed)."""
    result = sphinx_autodoc_pytest_fixtures._build_usage_snippet(
        "server", "Server", "resource", "function", autouse=False
    )
    assert result is None


def test_build_usage_snippet_autouse_returns_note() -> None:
    """Autouse fixtures return a nodes.note admonition."""

    result = sphinx_autodoc_pytest_fixtures._build_usage_snippet(
        "auto_cleanup", None, "resource", "function", autouse=True
    )
    assert isinstance(result, nodes.note)
    assert "No request needed" in result.astext()


def test_build_usage_snippet_factory_returns_literal_block() -> None:
    """Factory fixtures produce a literal_block with instantiation pattern."""

    result = sphinx_autodoc_pytest_fixtures._build_usage_snippet(
        "TestServer", "Server", "factory", "function", autouse=False
    )
    assert isinstance(result, nodes.literal_block)
    text = result.astext()
    assert "test_example" in text
    assert "TestServer()" in text
    assert ": Server" in text


def test_build_usage_snippet_override_hook_returns_conftest() -> None:
    """Override hook fixtures produce a conftest.py snippet."""

    result = sphinx_autodoc_pytest_fixtures._build_usage_snippet(
        "home_user", "str", "override_hook", "function", autouse=False
    )
    assert isinstance(result, nodes.literal_block)
    text = result.astext()
    assert "conftest.py" in text
    assert "@pytest.fixture\n" in text


def test_build_usage_snippet_override_hook_session_scope() -> None:
    """Override hook with session scope includes scope in decorator."""
    result = sphinx_autodoc_pytest_fixtures._build_usage_snippet(
        "home_user", "str", "override_hook", "session", autouse=False
    )
    assert result is not None
    text = result.astext()
    assert 'scope="session"' in text


def test_build_usage_snippet_override_hook_no_return_type() -> None:
    """Override hook without return type omits the arrow annotation."""
    result = sphinx_autodoc_pytest_fixtures._build_usage_snippet(
        "home_user", None, "override_hook", "function", autouse=False
    )
    assert result is not None
    text = result.astext()
    assert " -> " not in text


# ---------------------------------------------------------------------------
# autofixtures/auto-pytest-plugin helper composition
# ---------------------------------------------------------------------------


def _fake_document() -> t.Any:
    """Return a lightweight document-like object for directive helper tests."""
    env = types.SimpleNamespace(note_dependency=lambda _path: None)
    settings = types.SimpleNamespace(env=env)
    return types.SimpleNamespace(settings=settings)


def test_iter_public_fixture_entries_respects_excluded_names() -> None:
    """Fixture scanning omits excluded public names while preserving aliases."""

    @pytest.fixture(name="server")
    def _server() -> str:
        return "server"

    @pytest.fixture
    def auto_cleanup() -> str:
        return "cleanup"

    module = types.SimpleNamespace(
        __name__="fixture_mod",
        _server=_server,
        auto_cleanup=auto_cleanup,
        helper=lambda: "helper",
    )

    entries = spf_directives._iter_public_fixture_entries(
        module,
        excluded={"server"},
    )

    assert [public_name for _attr, public_name, _fixture in entries] == [
        "auto_cleanup",
    ]


def test_build_autofixtures_directive_text_sorts_and_adds_no_index() -> None:
    """Generated autofixture source preserves options without a Sphinx app."""
    entries = [
        ("b_fixture", "server", object()),
        ("a_fixture", "auto_cleanup", object()),
    ]

    content = spf_directives._build_autofixtures_directive_text(
        "fixture_mod",
        entries,
        order="alpha",
        no_index=True,
    )

    assert content == "\n".join(
        [
            ".. autofixture:: fixture_mod.auto_cleanup",
            "   :no-index:",
            "",
            ".. autofixture:: fixture_mod.server",
            "   :no-index:",
        ],
    )


def test_build_autofixtures_directive_text_wraps_eval_rst() -> None:
    """Native MyST wrapping is handled in pure string generation."""
    content = spf_directives._build_autofixtures_directive_text(
        "fixture_mod",
        [("my_server", "my_server", object())],
        wrap_eval_rst=True,
    )

    assert content.startswith("```{eval-rst}\n")
    assert content.endswith("\n```")


def test_autofixtures_directive_run_warns_on_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Import failures warn without needing a synthetic Sphinx build."""
    warning_calls: list[tuple[str, tuple[t.Any, ...]]] = []

    def _raise_import_error(_modname: str) -> t.Any:
        raise ImportError("boom")

    def _record_warning(message: str, *args: t.Any, **_kwargs: t.Any) -> None:
        warning_calls.append((message, args))

    fake_directive = types.SimpleNamespace(
        arguments=["fixture_mod"],
        options={},
        state=types.SimpleNamespace(document=_fake_document()),
    )
    monkeypatch.setattr(spf_directives.importlib, "import_module", _raise_import_error)
    monkeypatch.setattr(spf_directives.logger, "warning", _record_warning)

    result = spf_directives.AutofixturesDirective.run(fake_directive)

    assert result == []
    assert warning_calls == [
        ("autofixtures: cannot import module %r — skipping.", ("fixture_mod",))
    ]


def test_build_doc_pytest_plugin_intro_nodes_uses_generic_test_suite_text() -> None:
    """Generic intro copy stays generic when project is omitted."""
    intro_nodes = spf_directives._build_doc_pytest_plugin_intro_nodes(
        project="",
        summary="fixture-demo ships a pytest plugin.",
        install_command="uv add --dev fixture-demo",
        tests_url="https://example.com/fixture-demo/tests",
    )

    assert intro_nodes[0].astext() == "fixture-demo ships a pytest plugin."
    assert intro_nodes[-1].astext() == (
        "For real-world usage examples, see the test suite."
    )


def test_build_doc_pytest_plugin_fixture_section_scaffold_contains_index_node() -> None:
    """Fixture section scaffold is testable without parsing nested directives."""
    section_nodes = spf_directives._build_doc_pytest_plugin_fixture_section_scaffold(
        "fixture_mod"
    )

    assert [
        node.astext() for node in section_nodes if isinstance(node, nodes.rubric)
    ] == [
        "Fixture Summary",
        "Fixture Reference",
    ]
    assert isinstance(
        section_nodes[1],
        sphinx_autodoc_pytest_fixtures.autofixture_index_node,
    )
    assert section_nodes[1]["module"] == "fixture_mod"
    assert section_nodes[1]["exclude"] == set()


def test_compose_doc_pytest_plugin_nodes_orders_generated_sections() -> None:
    """Intro, body, and fixture sections stay in display order."""
    intro_nodes = [nodes.paragraph("", "intro")]
    body_nodes = [nodes.paragraph("", "body")]
    fixture_nodes = [nodes.paragraph("", "fixtures")]

    combined = spf_directives._compose_doc_pytest_plugin_nodes(
        intro_nodes=intro_nodes,
        body_nodes=body_nodes,
        fixture_section_nodes=fixture_nodes,
    )

    assert [node.astext() for node in combined] == ["intro", "body", "fixtures"]


def test_doc_pytest_plugin_require_option_raises_error() -> None:
    """Required options fail fast without a full directive parse."""
    fake_directive = types.SimpleNamespace(
        options={},
        name="auto-pytest-plugin",
        error=lambda message: RuntimeError(message),
    )

    with pytest.raises(RuntimeError, match="requires the :package: option"):
        spf_directives.AutoPytestPluginDirective._require_option(
            fake_directive,
            "package",
        )


def test_doc_pytest_plugin_get_module_fixture_entries_warns_when_no_fixtures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No-fixture warnings are visible without building a whole doctree."""
    warning_calls: list[tuple[str, tuple[t.Any, ...]]] = []

    def _record_warning(message: str, *args: t.Any, **_kwargs: t.Any) -> None:
        warning_calls.append((message, args))

    module = types.SimpleNamespace(
        __name__="fixture_mod",
        __file__="/tmp/fixture_mod.py",
        helper=lambda: "helper",
    )
    fake_directive = types.SimpleNamespace(
        state=types.SimpleNamespace(document=_fake_document()),
    )
    monkeypatch.setattr(spf_directives.importlib, "import_module", lambda _name: module)
    monkeypatch.setattr(spf_directives.logger, "warning", _record_warning)

    result = spf_directives.AutoPytestPluginDirective._get_module_fixture_entries(
        fake_directive,
        "fixture_mod",
    )

    assert result is None
    assert warning_calls == [
        (
            "auto-pytest-plugin found no pytest fixtures in %r; "
            "skipping generated fixture sections",
            ("fixture_mod",),
        )
    ]


def test_select_fixture_index_fixtures_respects_module_and_exclude() -> None:
    """Fixture index selection is pure filtering before xref resolution."""
    store: sphinx_autodoc_pytest_fixtures._store.FixtureStoreDict = {
        "fixtures": {
            "fixture_mod.server": _make_meta("fixture_mod.server", "server"),
            "fixture_mod.client": _make_meta("fixture_mod.client", "client"),
            "other_mod.server": _make_meta("other_mod.server", "server"),
        },
        "public_to_canon": {},
        "reverse_deps": {},
        "_store_version": sphinx_autodoc_pytest_fixtures._STORE_VERSION,
    }

    fixtures = spf_index._select_fixture_index_fixtures(
        store,
        "fixture_mod",
        {"client"},
    )

    assert [meta.canonical_name for meta in fixtures] == ["fixture_mod.server"]


def test_build_fixture_index_table_structure_contains_headers_badges_and_summary() -> (
    None
):
    """Fixture index table shell is inspectable without a Sphinx app."""
    meta = sphinx_autodoc_pytest_fixtures.FixtureMeta(
        docname="api",
        canonical_name="fixture_mod.old_server",
        public_name="old_server",
        source_name="old_server",
        scope="session",
        autouse=False,
        kind="resource",
        return_display="Server",
        deps=(),
        param_reprs=(),
        has_teardown=False,
        is_async=False,
        summary="Deprecated server fixture.",
        deprecated="2.0",
    )

    table, tbody = spf_index._build_fixture_index_table_structure([meta])

    assert isinstance(table, nodes.table)
    assert [entry.astext() for entry in table.findall(nodes.entry)][0:4] == [
        "Fixture",
        "Flags",
        "Returns",
        "Description",
    ]
    row = t.cast(nodes.row, tbody.children[0])
    assert row.children[0].astext() == "old_server"
    assert "fixture" in row.children[1].astext()
    assert "deprecated" in row.children[1].astext()
    assert row.children[2].astext() == "Server"
    assert row.children[3].astext() == "Deprecated server fixture."


# ---------------------------------------------------------------------------
# _on_env_purge_doc
# ---------------------------------------------------------------------------


def test_env_purge_doc_removes_only_target() -> None:
    """Purging a doc removes only that doc's fixtures from the store."""
    env = types.SimpleNamespace(
        domaindata={
            "sphinx_autodoc_pytest_fixtures": {
                "fixtures": {
                    "mod.fixture_a": sphinx_autodoc_pytest_fixtures.FixtureMeta(
                        docname="page_a",
                        canonical_name="mod.fixture_a",
                        public_name="fixture_a",
                        source_name="fixture_a",
                        scope="function",
                        autouse=False,
                        kind="resource",
                        return_display="str",
                        deps=(),
                        param_reprs=(),
                        has_teardown=False,
                        is_async=False,
                        summary="",
                    ),
                    "mod.fixture_b": sphinx_autodoc_pytest_fixtures.FixtureMeta(
                        docname="page_b",
                        canonical_name="mod.fixture_b",
                        public_name="fixture_b",
                        source_name="fixture_b",
                        scope="function",
                        autouse=False,
                        kind="resource",
                        return_display="str",
                        deps=(),
                        param_reprs=(),
                        has_teardown=False,
                        is_async=False,
                        summary="",
                    ),
                },
                "public_to_canon": {},
                "reverse_deps": {},
                "_store_version": sphinx_autodoc_pytest_fixtures._STORE_VERSION,
            },
        },
    )
    app = types.SimpleNamespace()
    sphinx_autodoc_pytest_fixtures._on_env_purge_doc(app, env, "page_a")
    store = env.domaindata["sphinx_autodoc_pytest_fixtures"]
    assert "mod.fixture_a" not in store["fixtures"]
    assert "mod.fixture_b" in store["fixtures"]


# ---------------------------------------------------------------------------
# FixtureMeta schema evolution — deprecated/replacement/teardown_summary
# ---------------------------------------------------------------------------


def test_fixture_meta_new_fields_default_to_none() -> None:
    """New optional fields default to None when not provided."""
    meta = _make_meta("mod.server", "server")
    assert meta.deprecated is None
    assert meta.replacement is None
    assert meta.teardown_summary is None


def test_fixture_meta_new_fields_accept_values() -> None:
    """New optional fields accept explicit values."""
    meta = sphinx_autodoc_pytest_fixtures.FixtureMeta(
        docname="api",
        canonical_name="mod.old_server",
        public_name="old_server",
        source_name="old_server",
        scope="function",
        autouse=False,
        kind="resource",
        return_display="Server",
        deps=(),
        param_reprs=(),
        has_teardown=True,
        is_async=False,
        summary="Deprecated server fixture.",
        deprecated="2.0",
        replacement="mod.new_server",
        teardown_summary="Kills the tmux server process.",
    )
    assert meta.deprecated == "2.0"
    assert meta.replacement == "mod.new_server"
    assert meta.teardown_summary == "Kills the tmux server process."


# ---------------------------------------------------------------------------
# Deprecation badge rendering
# ---------------------------------------------------------------------------


def test_deprecated_badge_renders_at_slot_zero() -> None:
    """Deprecated badge appears as leftmost badge (slot 0)."""
    node = sphinx_autodoc_pytest_fixtures._build_badge_group_node(
        "session", "resource", False, deprecated=True
    )
    badges = [c for c in node.children if isinstance(c, BadgeNode)]
    assert len(badges) >= 2
    # First badge should be "deprecated"
    assert badges[0].astext() == "deprecated"
    classes_first: list[str] = badges[0].get("classes", [])
    assert SAB.STATE_DEPRECATED in classes_first


def test_deprecated_badge_absent_when_not_deprecated() -> None:
    """No deprecated badge when deprecated=False (default)."""
    node = sphinx_autodoc_pytest_fixtures._build_badge_group_node(
        "session", "resource", False
    )
    badges = [c for c in node.children if isinstance(c, BadgeNode)]
    texts = [b.astext() for b in badges]
    assert "deprecated" not in texts


# ---------------------------------------------------------------------------
# Build-time validation (SPF001-SPF006)
# ---------------------------------------------------------------------------


def test_spf001_missing_docstring(caplog: pytest.LogCaptureFixture) -> None:
    """SPF001 fires for fixtures with empty summary."""
    import logging

    from sphinx_autodoc_pytest_fixtures._validation import _validate_store

    store: sphinx_autodoc_pytest_fixtures._store.FixtureStoreDict = {
        "fixtures": {
            "mod.bare": _make_meta("mod.bare", "bare"),
        },
        "public_to_canon": {"bare": "mod.bare"},
        "reverse_deps": {},
        "_store_version": sphinx_autodoc_pytest_fixtures._STORE_VERSION,
    }
    # Override summary to empty
    import dataclasses

    store["fixtures"]["mod.bare"] = dataclasses.replace(
        store["fixtures"]["mod.bare"], summary=""
    )

    app = types.SimpleNamespace(
        config=types.SimpleNamespace(pytest_fixture_lint_level="warning")
    )
    with caplog.at_level(
        logging.WARNING, logger="sphinx_autodoc_pytest_fixtures._validation"
    ):
        _validate_store(store, app)

    spf001 = [r for r in caplog.records if getattr(r, "spf_code", None) == "SPF001"]
    assert len(spf001) == 1


def test_spf005_deprecated_without_replacement(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """SPF005 fires for deprecated fixtures without replacement."""
    import dataclasses
    import logging

    from sphinx_autodoc_pytest_fixtures._validation import _validate_store

    meta = dataclasses.replace(
        _make_meta("mod.old", "old"), deprecated="2.0", replacement=None
    )
    store: sphinx_autodoc_pytest_fixtures._store.FixtureStoreDict = {
        "fixtures": {"mod.old": meta},
        "public_to_canon": {"old": "mod.old"},
        "reverse_deps": {},
        "_store_version": sphinx_autodoc_pytest_fixtures._STORE_VERSION,
    }
    app = types.SimpleNamespace(
        config=types.SimpleNamespace(pytest_fixture_lint_level="warning")
    )
    with caplog.at_level(
        logging.WARNING, logger="sphinx_autodoc_pytest_fixtures._validation"
    ):
        _validate_store(store, app)

    spf005 = [r for r in caplog.records if getattr(r, "spf_code", None) == "SPF005"]
    assert len(spf005) == 1


def test_validation_silent_when_lint_level_none(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """lint_level='none' suppresses all validation warnings."""
    import dataclasses
    import logging

    from sphinx_autodoc_pytest_fixtures._validation import _validate_store

    meta = dataclasses.replace(_make_meta("mod.bare", "bare"), summary="")
    store: sphinx_autodoc_pytest_fixtures._store.FixtureStoreDict = {
        "fixtures": {"mod.bare": meta},
        "public_to_canon": {"bare": "mod.bare"},
        "reverse_deps": {},
        "_store_version": sphinx_autodoc_pytest_fixtures._STORE_VERSION,
    }
    app = types.SimpleNamespace(
        config=types.SimpleNamespace(pytest_fixture_lint_level="none")
    )
    with caplog.at_level(
        logging.WARNING, logger="sphinx_autodoc_pytest_fixtures._validation"
    ):
        _validate_store(store, app)

    assert len(caplog.records) == 0


def test_lint_level_error_uses_logger_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """lint_level='error' emits ERROR-level records and sets statuscode=1."""
    import dataclasses
    import logging

    from sphinx_autodoc_pytest_fixtures._validation import _validate_store

    meta = dataclasses.replace(_make_meta("mod.bare", "bare"), summary="")
    store: sphinx_autodoc_pytest_fixtures._store.FixtureStoreDict = {
        "fixtures": {"mod.bare": meta},
        "public_to_canon": {"bare": "mod.bare"},
        "reverse_deps": {},
        "_store_version": sphinx_autodoc_pytest_fixtures._STORE_VERSION,
    }
    app = types.SimpleNamespace(
        config=types.SimpleNamespace(pytest_fixture_lint_level="error"),
        statuscode=0,
    )
    with caplog.at_level(
        logging.DEBUG, logger="sphinx_autodoc_pytest_fixtures._validation"
    ):
        _validate_store(store, app)

    spf001 = [r for r in caplog.records if getattr(r, "spf_code", None) == "SPF001"]
    assert len(spf001) == 1
    assert spf001[0].levelno == logging.ERROR
    assert app.statuscode == 1


def test_spf002_missing_return_annotation(caplog: pytest.LogCaptureFixture) -> None:
    """SPF002 fires for fixtures with empty return annotation."""
    import dataclasses
    import logging

    from sphinx_autodoc_pytest_fixtures._validation import _validate_store

    meta = dataclasses.replace(_make_meta("mod.bare", "bare"), return_display="...")
    store: sphinx_autodoc_pytest_fixtures._store.FixtureStoreDict = {
        "fixtures": {"mod.bare": meta},
        "public_to_canon": {"bare": "mod.bare"},
        "reverse_deps": {},
        "_store_version": sphinx_autodoc_pytest_fixtures._STORE_VERSION,
    }
    app = types.SimpleNamespace(
        config=types.SimpleNamespace(pytest_fixture_lint_level="warning")
    )
    with caplog.at_level(
        logging.WARNING, logger="sphinx_autodoc_pytest_fixtures._validation"
    ):
        _validate_store(store, app)

    spf002 = [r for r in caplog.records if getattr(r, "spf_code", None) == "SPF002"]
    assert len(spf002) == 1


def test_spf003_yield_missing_teardown(caplog: pytest.LogCaptureFixture) -> None:
    """SPF003 fires for yield fixtures without teardown documentation."""
    import dataclasses
    import logging

    from sphinx_autodoc_pytest_fixtures._validation import _validate_store

    meta = dataclasses.replace(
        _make_meta("mod.gen", "gen"),
        has_teardown=True,
        teardown_summary=None,
    )
    store: sphinx_autodoc_pytest_fixtures._store.FixtureStoreDict = {
        "fixtures": {"mod.gen": meta},
        "public_to_canon": {"gen": "mod.gen"},
        "reverse_deps": {},
        "_store_version": sphinx_autodoc_pytest_fixtures._STORE_VERSION,
    }
    app = types.SimpleNamespace(
        config=types.SimpleNamespace(pytest_fixture_lint_level="warning")
    )
    with caplog.at_level(
        logging.WARNING, logger="sphinx_autodoc_pytest_fixtures._validation"
    ):
        _validate_store(store, app)

    spf003 = [r for r in caplog.records if getattr(r, "spf_code", None) == "SPF003"]
    assert len(spf003) == 1


def test_spf006_ambiguous_public_name(caplog: pytest.LogCaptureFixture) -> None:
    """SPF006 fires when a public name maps to multiple canonical names."""
    import logging

    from sphinx_autodoc_pytest_fixtures._validation import _validate_store

    store: sphinx_autodoc_pytest_fixtures._store.FixtureStoreDict = {
        "fixtures": {
            "mod_a.server": _make_meta("mod_a.server", "server"),
            "mod_b.server": _make_meta("mod_b.server", "server"),
        },
        "public_to_canon": {"server": None},  # ambiguous
        "reverse_deps": {},
        "_store_version": sphinx_autodoc_pytest_fixtures._STORE_VERSION,
    }
    app = types.SimpleNamespace(
        config=types.SimpleNamespace(pytest_fixture_lint_level="warning")
    )
    with caplog.at_level(
        logging.WARNING, logger="sphinx_autodoc_pytest_fixtures._validation"
    ):
        _validate_store(store, app)

    spf006 = [r for r in caplog.records if getattr(r, "spf_code", None) == "SPF006"]
    assert len(spf006) == 1


# ---------------------------------------------------------------------------
# _qualify_forward_ref — TYPE_CHECKING forward-reference resolution
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not HAS_LIBTMUX,
    reason="requires libtmux",
)
def test_qualify_forward_ref_resolves_type_checking_import() -> None:
    """_qualify_forward_ref resolves TYPE_CHECKING imports via AST parsing."""
    from libtmux.pytest_plugin import session

    from sphinx_autodoc_pytest_fixtures._metadata import _qualify_forward_ref

    fn = sphinx_autodoc_pytest_fixtures._get_fixture_fn(session)
    result = _qualify_forward_ref("Session", fn)
    assert result == "libtmux.session.Session"


@pytest.mark.skipif(
    not HAS_LIBTMUX,
    reason="requires libtmux",
)
def test_qualify_forward_ref_returns_none_for_unknown() -> None:
    """_qualify_forward_ref returns None for names not found in module imports."""
    from libtmux.pytest_plugin import server

    from sphinx_autodoc_pytest_fixtures._metadata import _qualify_forward_ref

    fn = sphinx_autodoc_pytest_fixtures._get_fixture_fn(server)
    result = _qualify_forward_ref("NonexistentClass", fn)
    assert result is None


def test_qualify_forward_ref_prefers_type_checking_block_over_runtime_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TYPE_CHECKING-guarded import wins over a same-name runtime import."""
    import sys

    from sphinx_autodoc_pytest_fixtures import _metadata as spf_meta
    from sphinx_autodoc_pytest_fixtures._metadata import _qualify_forward_ref

    synthetic_source = """\
from __future__ import annotations
import typing as t
from mod_a import Foo  # runtime import
if t.TYPE_CHECKING:
    from mod_b import Foo  # TYPE_CHECKING import — should win
"""
    fake_mod = types.ModuleType("fake_qual_mod")
    sys.modules["fake_qual_mod"] = fake_mod

    def fake_fn() -> Foo:  # type: ignore[name-defined]  # noqa: F821
        pass

    fake_fn.__module__ = "fake_qual_mod"
    monkeypatch.setattr(spf_meta.inspect, "getsource", lambda _: synthetic_source)

    result = _qualify_forward_ref("Foo", fake_fn)
    # Pre-fix: "mod_a.Foo" (runtime import wins via first-match AST walk)
    # Post-fix: "mod_b.Foo" (TYPE_CHECKING block wins)
    assert result == "mod_b.Foo"

    del sys.modules["fake_qual_mod"]


@pytest.mark.skipif(
    not HAS_LIBTMUX,
    reason="requires libtmux",
)
def test_qualify_forward_ref_no_source_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_qualify_forward_ref returns None when inspect.getsource raises OSError."""
    from libtmux.pytest_plugin import session

    from sphinx_autodoc_pytest_fixtures import _metadata as spf_meta
    from sphinx_autodoc_pytest_fixtures._metadata import _qualify_forward_ref

    fn = sphinx_autodoc_pytest_fixtures._get_fixture_fn(session)
    monkeypatch.setattr(
        spf_meta.inspect,
        "getsource",
        lambda _: (_ for _ in ()).throw(OSError("no source")),
    )
    result = _qualify_forward_ref("Session", fn)
    assert result is None


# ---------------------------------------------------------------------------
# _extract_summary
# ---------------------------------------------------------------------------


def test_extract_summary_single_sentence() -> None:
    """_extract_summary returns the first sentence when it ends with a period."""
    from sphinx_autodoc_pytest_fixtures._metadata import _extract_summary

    @pytest.fixture
    def my_fix() -> str:
        """Return a string. This second sentence should be excluded."""
        return "x"

    assert _extract_summary(my_fix) == "Return a string."


def test_extract_summary_sentence_at_eof() -> None:
    """_extract_summary handles first paragraph whose last sentence ends at EOF."""
    from sphinx_autodoc_pytest_fixtures._metadata import _extract_summary

    @pytest.fixture
    def my_fix() -> str:
        """First sentence. Second sentence ends here."""
        return "x"

    # The last sentence ends at EOF with no trailing whitespace — regex must match.
    assert _extract_summary(my_fix) == "First sentence."


def test_extract_summary_no_sentence_terminator() -> None:
    """_extract_summary falls back to first_para when no sentence terminator exists."""
    from sphinx_autodoc_pytest_fixtures._metadata import _extract_summary

    @pytest.fixture
    def my_fix() -> str:
        """A fixture with no sentence terminator"""  # noqa: D400, D401
        return "x"

    assert _extract_summary(my_fix) == "A fixture with no sentence terminator"
