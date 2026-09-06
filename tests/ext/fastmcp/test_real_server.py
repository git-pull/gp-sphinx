"""Collector tests against a real FastMCP server.

The other tests build components from hand-written shims, which cannot
catch a rename in FastMCP's own object model: a stub keeps answering the
spelling it was written with. These build a real server instead, so an
SDK field rename fails here rather than silently emptying a docs page.

FastMCP is a dev-only dependency; the extension itself works without it.
"""

from __future__ import annotations

import asyncio
import logging
import re
import types
import typing as t
import warnings

import pytest

from sphinx_autodoc_fastmcp._collector import (
    _annotation_hints,
    _index_by_unique_name,
    _iter_components,
    _params_from_schema,
    _prompt_from_component,
    _resource_from_component,
    _schema_type_text,
    _tool_from_component,
    _tools_from_server,
    collect_tools,
)

pytest.importorskip("fastmcp")

from fastmcp import Context, FastMCP  # noqa: E402
from fastmcp.prompts import Prompt as _Prompt  # noqa: E402
from fastmcp.resources import Resource as _Resource  # noqa: E402
from fastmcp.tools import Tool as _Tool  # noqa: E402
from mcp.types import Annotations, ToolAnnotations  # noqa: E402

_LAST_MODIFIED = "2026-01-01T00:00:00Z"


class Fixture(t.NamedTuple):
    """A server plus the decorated tool, which carries its own spec."""

    server: FastMCP
    tool: t.Any


@pytest.fixture(scope="module")
def fixture() -> Fixture:
    """A server exercising every annotation the collector reads."""
    app: FastMCP = FastMCP("collector-fixture")

    @app.tool(
        annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False),
    )
    def inspect_thing(count: int) -> str:
        """Look at a thing."""
        return "looked"

    @app.resource(
        "fixture://thing",
        annotations=Annotations(last_modified=_LAST_MODIFIED),
    )
    def thing() -> str:
        """A thing."""
        return "{}"

    @app.prompt
    def describe(count: int) -> str:
        """Describe some things."""
        return "described"

    return Fixture(server=app, tool=inspect_thing)


def test_tool_hints_survive_the_object_model(fixture: Fixture) -> None:
    """Hints reach the vocabulary without leaning on the camelCase bridge.

    FastMCP answers the SDK v1 spellings through a warn-once shim it plans
    to remove, so reading them still works and would keep a value-only
    assertion green. Failing on the warning is what makes this test notice
    the removal before a docs build does.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        hints = _annotation_hints(fixture.tool.__fastmcp__.annotations)

    assert hints == {"readOnlyHint": True, "destructiveHint": False}


def test_a_mapping_of_hints_is_read_by_its_documented_name() -> None:
    """Callers passing a plain mapping keep working."""
    assert _annotation_hints({"readOnlyHint": True, "openWorldHint": None}) == {
        "readOnlyHint": True,
    }


@pytest.mark.asyncio
async def test_resource_last_modified_survives_the_object_model(
    fixture: Fixture,
) -> None:
    """A resource's last-modified annotation reaches the page."""
    resource = await fixture.server.get_resource("fixture://thing")

    info = _resource_from_component(resource)

    assert info.annotations["lastModified"] == _LAST_MODIFIED


@pytest.mark.asyncio
async def test_prompt_arguments_drop_the_generated_schema_note(
    fixture: Fixture,
) -> None:
    """FastMCP's schema hint is stripped whatever its current wording."""
    prompt = await fixture.server.get_prompt("describe")

    info = _prompt_from_component(prompt)

    assert "JSON" not in info.arguments[0].description


def test_a_configured_server_yields_tools_the_mock_would_drop() -> None:
    """A kwarg the mock rejects must not erase its module's other tools.

    ``collect_tools``' register mode drives a hand-written collector whose
    signature lags FastMCP's, and its module loop swallows the resulting
    ``TypeError`` with a warning — so one unknown kwarg silently drops the
    rest of the module. Reading the live server instead sees what is served.
    """
    server = FastMCP("drop-probe")

    @server.tool(title="Alpha")
    def alpha() -> str:
        """First."""
        return "a"

    @server.tool(title="Beta", version="2")
    async def beta() -> str:
        """Second."""
        return "b"

    @server.tool(title="Gamma")
    def gamma() -> str:
        """Third."""
        return "c"

    collected = _tools_from_server(server, area_map={}, axes=())

    assert collected is not None
    assert sorted(info.name for info in collected) == ["alpha", "beta", "gamma"]


def test_duplicate_tool_names_warn_instead_of_vanishing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Two tools sharing a name must not silently become one.

    FastMCP keys tools by name but permits duplicates that differ another
    way (a version, say), so both are really served. Keying the docs index
    by name alone dropped one with no signal.
    """
    server = FastMCP("dup-probe")

    @server.tool(name="same", version="1")
    def first() -> str:
        """First."""
        return "1"

    @server.tool(name="same", version="2")
    def second() -> str:
        """Second."""
        return "2"

    collected = _tools_from_server(server, area_map={}, axes=())
    assert collected is not None
    assert len(collected) == 2, "both registrations should reach the collector"

    index: dict[str, object] = {}
    with caplog.at_level(logging.WARNING):
        for info in collected:
            _index_by_unique_name(index, info.name, info, "tool")

    assert list(index) == ["same"]
    assert any("duplicate tool name" in r.getMessage() for r in caplog.records)


def test_collected_tools_survive_environment_pickling() -> None:
    """Sphinx pickles its environment; a collected tool must survive it.

    Tools registered inside a ``register(mcp)`` factory are closures, and
    pickling one raises — which broke incremental builds for every project
    that registers tools that way.
    """
    import pickle

    server = FastMCP("pickle-probe")

    def register(app: FastMCP) -> None:
        @app.tool(title="Local")
        def made_in_a_closure() -> str:
            """Registered inside a factory."""
            return "x"

    register(server)
    collected = _tools_from_server(server, area_map={}, axes=())
    assert collected is not None

    restored = pickle.loads(pickle.dumps(collected))

    assert [info.name for info in restored] == ["made_in_a_closure"]
    assert restored[0].docstring == "Registered inside a factory."


def test_injected_context_is_not_documented() -> None:
    """A tool's injected ``Context`` stays out of the parameter table.

    FastMCP drops it from the published schema because no caller can pass
    it, so a table built from the signature would document an argument the
    server does not accept.
    """
    app: FastMCP = FastMCP("context-fixture")

    @app.tool
    def search(terms: str, ctx: Context) -> str:
        """Search."""
        return "ok"

    collected = _tools_from_server(app, area_map={}, axes=())
    assert collected is not None
    names = [param.name for param in collected[0].params]
    assert names == ["terms"]


def test_parameter_defaults_are_reproducible() -> None:
    """No parameter default carries an object address.

    A default rendered through ``str()`` puts the repr of a sentinel into
    the HTML, so two builds of one source produce different bytes.
    """
    app: FastMCP = FastMCP("default-fixture")

    @app.tool
    def search(terms: str, ctx: Context) -> str:
        """Search."""
        return "ok"

    collected = _tools_from_server(app, area_map={}, axes=())
    assert collected is not None
    rendered = repr([param.default for param in collected[0].params])
    assert not re.search(r"0x[0-9a-f]{6,}", rendered), rendered


def test_v1_annotation_attributes_are_still_read() -> None:
    """A tool built against MCP SDK v1 keeps its hints.

    v1 published the documented camelCase names as the attributes. Reading
    only the v2 field names would empty the badge vocabulary for those
    consumers, and the extension declares no version floor.
    """
    v1_style = types.SimpleNamespace(readOnlyHint=True, destructiveHint=False)

    assert _annotation_hints(v1_style) == {
        "readOnlyHint": True,
        "destructiveHint": False,
    }


def test_a_tool_without_a_python_callable_is_still_documented() -> None:
    """A proxied or provider-backed tool reaches the page.

    ``ProxyTool`` and ``FastMCPProviderTool`` carry no ``fn``; filtering on
    one drops every tool a mounted or proxied server contributes, which is
    the silent-loss bug the live-server path exists to remove.
    """
    app: FastMCP = FastMCP("fnless-fixture")

    @app.tool
    def real(a: int) -> str:
        """Real."""
        return "ok"

    fnless = types.SimpleNamespace(
        name="proxied",
        title=None,
        tags=None,
        meta=None,
        annotations=None,
        parameters={"properties": {"a": {"type": "integer"}}, "required": ["a"]},
        fn=None,
    )
    info = _tool_from_component(fnless, area_map={})
    assert info.name == "proxied"
    assert [param.name for param in info.params] == ["a"]


@pytest.mark.parametrize("namespace", [None, "kid"])
def test_mounted_tools_match_what_the_server_serves(namespace: str | None) -> None:
    """A mounted child server's tools are documented under their served names.

    The parent's own registry does not hold them, so reading it alone
    documented one tool where the server served two. A namespaced mount also
    renames what it carries, and a name the server does not serve is worse
    than a missing page.
    """
    child: FastMCP = FastMCP("child")

    @child.tool
    def child_tool(a: int) -> str:
        """Child."""
        return "ok"

    parent: FastMCP = FastMCP("parent")

    @parent.tool
    def parent_tool(b: int) -> str:
        """Parent."""
        return "ok"

    if namespace is None:
        parent.mount(child)
    else:
        parent.mount(child, namespace=namespace)

    collected = _tools_from_server(parent, area_map={}, axes=())
    assert collected is not None
    served = asyncio.run(parent.list_tools(run_middleware=False))

    assert sorted(tool.name for tool in collected) == sorted(
        tool.name for tool in served
    )


@pytest.mark.parametrize("namespace", [None, "one"])
def test_mounted_components_match_what_the_server_serves(
    namespace: str | None,
) -> None:
    """Every component kind is documented under its served identity.

    A namespace moves into a resource's URI and into a tool's name, so
    checking tools alone proves nothing about resources.
    """
    child: FastMCP = FastMCP("child")

    @child.tool
    def child_tool(a: int) -> str:
        """Child tool."""
        return "ok"

    @child.resource("data://thing")
    def child_resource() -> str:
        """Child resource."""
        return "{}"

    @child.prompt
    def child_prompt(a: int) -> str:
        """Child prompt."""
        return "drafted"

    parent: FastMCP = FastMCP("parent")
    if namespace is None:
        parent.mount(child)
    else:
        parent.mount(child, namespace=namespace)

    walked = _iter_components(parent)
    assert sorted(tool.name for tool in walked if isinstance(tool, _Tool)) == sorted(
        tool.name for tool in asyncio.run(parent.list_tools(run_middleware=False))
    )
    assert sorted(
        str(res.uri) for res in walked if isinstance(res, _Resource)
    ) == sorted(
        str(res.uri) for res in asyncio.run(parent.list_resources(run_middleware=False))
    )
    assert sorted(
        prompt.name for prompt in walked if isinstance(prompt, _Prompt)
    ) == sorted(
        prompt.name for prompt in asyncio.run(parent.list_prompts(run_middleware=False))
    )


def test_one_child_mounted_twice_is_served_twice() -> None:
    """A child mounted under two namespaces is two served components.

    Suppressing an already-visited server treats the second mount as a
    cycle and drops it, though the server publishes both names.
    """
    child: FastMCP = FastMCP("child")

    @child.tool
    def hello(a: int) -> str:
        """Hello."""
        return "ok"

    parent: FastMCP = FastMCP("parent")
    parent.mount(child, namespace="one")
    parent.mount(child, namespace="two")

    assert sorted(
        tool.name for tool in _iter_components(parent) if isinstance(tool, _Tool)
    ) == sorted(
        tool.name for tool in asyncio.run(parent.list_tools(run_middleware=False))
    )


def test_nested_mounts_nest_their_namespaces_in_order() -> None:
    """An inner namespace applies before the one it is mounted under."""
    inner: FastMCP = FastMCP("inner")

    @inner.tool
    def hello(a: int) -> str:
        """Hello."""
        return "ok"

    @inner.resource("data://thing")
    def thing() -> str:
        """Thing."""
        return "{}"

    mid: FastMCP = FastMCP("mid")
    mid.mount(inner, namespace="inner")
    outer: FastMCP = FastMCP("outer")
    outer.mount(mid, namespace="outer")

    walked = _iter_components(outer)
    assert sorted(tool.name for tool in walked if isinstance(tool, _Tool)) == sorted(
        tool.name for tool in asyncio.run(outer.list_tools(run_middleware=False))
    )
    assert sorted(
        str(res.uri) for res in walked if isinstance(res, _Resource)
    ) == sorted(
        str(res.uri) for res in asyncio.run(outer.list_resources(run_middleware=False))
    )


def test_a_transform_on_the_server_renames_what_it_serves() -> None:
    """A namespace added to the server itself reaches its components."""
    from fastmcp.server.transforms import Namespace

    server: FastMCP = FastMCP("server")

    @server.tool
    def hi(a: int) -> str:
        """Hi."""
        return "ok"

    server.add_transform(Namespace("public"))

    assert sorted(
        tool.name for tool in _iter_components(server) if isinstance(tool, _Tool)
    ) == sorted(
        tool.name for tool in asyncio.run(server.list_tools(run_middleware=False))
    )


def test_a_tool_without_a_callable_keeps_its_description() -> None:
    """A component with no ``fn`` still explains itself.

    Both the card and the summary read ``ToolInfo.docstring``.
    """
    fnless = types.SimpleNamespace(
        name="proxied",
        title=None,
        tags=None,
        meta=None,
        annotations=None,
        description="What the proxied tool does.",
        parameters={},
        fn=None,
    )

    assert _tool_from_component(fnless, area_map={}).docstring == (
        "What the proxied tool does."
    )


def test_a_schema_union_keeps_every_alternative() -> None:
    """A union parameter documents all its accepted types."""
    assert _schema_type_text({"anyOf": [{"type": "integer"}, {"type": "string"}]}) == (
        "integer | string"
    )


@pytest.mark.parametrize(
    "mount_kwargs",
    [
        {"tool_names": {"hello": "greet"}},
        {"namespace": "ns", "tool_names": {"hello": "greet"}},
    ],
    ids=["rename", "namespace+rename"],
)
def test_a_renamed_mount_is_documented_under_its_served_name(
    mount_kwargs: dict[str, t.Any],
) -> None:
    """``mount(..., tool_names=...)`` renames through a second wrapper.

    A namespace around a rename wraps the provider twice; peeling one
    layer found nothing and said nothing.
    """
    child: FastMCP = FastMCP("child")

    @child.tool
    def hello(a: int) -> str:
        """Hello."""
        return "ok"

    parent: FastMCP = FastMCP("parent")
    parent.mount(child, **mount_kwargs)

    assert sorted(
        tool.name for tool in _iter_components(parent) if isinstance(tool, _Tool)
    ) == sorted(
        tool.name for tool in asyncio.run(parent.list_tools(run_middleware=False))
    )


def test_a_transform_on_a_provider_renames_what_it_holds() -> None:
    """``provider.add_transform`` is honoured without a mount around it."""
    from fastmcp.server.transforms import Namespace

    child: FastMCP = FastMCP("child")

    @child.tool
    def hello(a: int) -> str:
        """Hello."""
        return "ok"

    child.local_provider.add_transform(Namespace("api"))
    parent: FastMCP = FastMCP("parent")
    parent.mount(child)

    assert sorted(
        tool.name for tool in _iter_components(parent) if isinstance(tool, _Tool)
    ) == sorted(
        tool.name for tool in asyncio.run(parent.list_tools(run_middleware=False))
    )


def test_a_module_tool_colliding_with_a_served_tool_is_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The server wins a shared name, and the module entry is warned about.

    Merging with a bare dict update discarded the module entry in silence,
    bypassing the collision report every other same-kind duplicate gets.
    """
    import sys

    def list_sessions(server: str) -> list[str]:
        """Module copy."""
        return []

    t.cast(t.Any, list_sessions).__fastmcp__ = types.SimpleNamespace(
        name="list_sessions", title="List", tags=set(), annotations=None
    )
    module = types.ModuleType("collision_mod")
    module.list_sessions = list_sessions  # type: ignore[attr-defined]
    sys.modules["collision_mod"] = module

    app: FastMCP = FastMCP("served")

    @app.tool
    def list_sessions_served(server: str) -> list[str]:
        """Served copy."""
        return []

    app.local_provider.remove_tool("list_sessions_served")

    @app.tool(name="list_sessions")
    def served(server: str) -> list[str]:
        """Served copy."""
        return []

    class _Env:
        pass

    class _Config:
        fastmcp_server_module = "x"
        fastmcp_tool_modules = ["collision_mod"]
        fastmcp_area_map: dict[str, str] = {}
        fastmcp_axes: tuple[t.Any, ...] = ()
        fastmcp_collector_mode = "introspect"

    class _App:
        config = _Config()
        env = _Env()

    fake = _App()
    fake._fastmcp_server_cache = ("x", app)  # type: ignore[attr-defined]
    try:
        with caplog.at_level(logging.WARNING):
            collect_tools(t.cast(t.Any, fake))
    finally:
        del sys.modules["collision_mod"]

    documented = t.cast(t.Any, fake.env).fastmcp_tools
    assert documented["list_sessions"].docstring == "Served copy."
    assert any("duplicate tool name" in rec.message for rec in caplog.records)


def test_a_child_transform_applies_before_its_mount_namespace() -> None:
    """A child's own namespace nests inside the one it is mounted under."""
    from fastmcp.server.transforms import Namespace

    child: FastMCP = FastMCP("child")

    @child.tool
    def hello(a: int) -> str:
        """Hello."""
        return "ok"

    @child.resource("data://thing")
    def thing() -> str:
        """Thing."""
        return "{}"

    child.add_transform(Namespace("inner"))
    parent: FastMCP = FastMCP("parent")
    parent.mount(child, namespace="outer")

    walked = _iter_components(parent)
    assert sorted(tool.name for tool in walked if isinstance(tool, _Tool)) == sorted(
        tool.name for tool in asyncio.run(parent.list_tools(run_middleware=False))
    )
    assert sorted(
        str(res.uri) for res in walked if isinstance(res, _Resource)
    ) == sorted(
        str(res.uri) for res in asyncio.run(parent.list_resources(run_middleware=False))
    )


def test_a_transformed_provider_added_under_a_namespace_keeps_both() -> None:
    """``add_provider`` around a provider with its own transform nests both."""
    from fastmcp.server.transforms import Namespace

    provider = type(FastMCP("x").local_provider)()

    @provider.tool
    def ping() -> str:
        """Ping."""
        return "ok"

    provider.add_transform(Namespace("inner"))
    parent: FastMCP = FastMCP("parent")
    parent.add_provider(provider, namespace="outer")

    assert sorted(
        tool.name for tool in _iter_components(parent) if isinstance(tool, _Tool)
    ) == sorted(
        tool.name for tool in asyncio.run(parent.list_tools(run_middleware=False))
    )


def test_an_absent_schema_default_is_not_documented_as_none() -> None:
    """A ``default_factory`` parameter publishes no default, and ``None`` is
    a value it does not accept."""
    from pydantic import Field

    app: FastMCP = FastMCP("defaults")

    @app.tool
    def search(
        filters: list[str] = Field(default_factory=list),
        explicit: str | None = None,
    ) -> str:
        """Search."""
        return "ok"

    collected = _tools_from_server(app, area_map={}, axes=())
    assert collected is not None
    defaults = {param.name: param.default for param in collected[0].params}
    assert defaults == {"filters": "", "explicit": "None"}


def test_a_boolean_subschema_does_not_abort_collection() -> None:
    """``{"properties": {"payload": true}}`` is valid JSON Schema.

    A boolean carries no fields to read; documenting the name with no type
    beats failing the build.
    """
    rows = _params_from_schema({"properties": {"payload": True}}, lambda payload: None)

    assert [(row.name, row.type_str) for row in rows] == [("payload", "")]


def test_a_provider_without_a_registry_is_named_in_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A dynamic provider that lists only asynchronously is reported.

    Skipping it in silence documents an empty index for a server that
    serves tools.
    """

    class Dynamic:
        transforms: tuple[t.Any, ...] = ()

        async def _list_tools(self) -> list[t.Any]:
            return []

    server: FastMCP = FastMCP("server")
    server.add_provider(t.cast(t.Any, Dynamic()))

    with caplog.at_level(logging.WARNING):
        _iter_components(server)

    assert any("Dynamic" in rec.message for rec in caplog.records)


def test_a_tool_transform_is_applied_in_full() -> None:
    """A rename map changes title and arguments, not only the tool name."""
    from fastmcp.server.transforms import ToolTransform
    from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig

    child: FastMCP = FastMCP("child")

    @child.tool
    def search(raw_query: str) -> str:
        """Search."""
        return "ok"

    child.local_provider.add_transform(
        ToolTransform(
            {
                "search": ToolTransformConfig(
                    name="lookup",
                    title="Look Up",
                    arguments={"raw_query": ArgTransformConfig(name="query")},
                )
            }
        )
    )
    parent: FastMCP = FastMCP("parent")
    parent.mount(child, namespace="ns")

    collected = _tools_from_server(parent, area_map={}, axes=())
    assert collected is not None
    served = asyncio.run(parent.list_tools(run_middleware=False))

    assert [
        (info.name, info.title, [param.name for param in info.params])
        for info in collected
    ] == [
        (tool.name, tool.title, sorted(tool.parameters.get("properties", {})))
        for tool in served
    ]


def test_a_description_kwarg_survives_an_undocumented_function() -> None:
    """``@tool(description=...)`` is the tool's explanation when the
    function has no docstring."""
    app: FastMCP = FastMCP("described")

    @app.tool(description="Fetch the selected user record.")
    def fetch(user_id: int) -> str:
        return "ok"

    collected = _tools_from_server(app, area_map={}, axes=())
    assert collected is not None
    assert collected[0].docstring == "Fetch the selected user record."


def test_a_tool_transform_leaves_a_same_named_template_alone() -> None:
    """A rename map targets tools only.

    A resource template also carries ``parameters``; applying a tool
    transform to it raised and aborted the build.
    """
    from fastmcp.server.transforms import ToolTransform
    from fastmcp.tools.tool_transform import ToolTransformConfig

    server: FastMCP = FastMCP("server")

    @server.tool
    def hello(a: int) -> str:
        """Hello."""
        return "ok"

    @server.resource("data://hello/{x}", name="hello")
    def hello_template(x: str) -> str:
        """Template."""
        return "{}"

    server.local_provider.add_transform(
        ToolTransform({"hello": ToolTransformConfig(name="hi")})
    )

    assert sorted(
        f"{type(component).__name__}:{component.name}"
        for component in _iter_components(server)
    ) == ["FunctionResourceTemplate:hello", "TransformedTool:hi"]


def test_a_renamed_tool_keeps_its_source_module() -> None:
    """Area attribution follows the tool a transform was made from.

    The forwarding callable lives in FastMCP's own module; attributing to
    it broke every summary link for a renamed tool.
    """
    child: FastMCP = FastMCP("child")

    @child.tool
    def hello(a: int) -> str:
        """Hello."""
        return "ok"

    parent: FastMCP = FastMCP("parent")
    parent.mount(child, tool_names={"hello": "greet"})

    collected = _tools_from_server(
        parent, area_map={__name__.rpartition(".")[2]: "my/area"}, axes=()
    )
    assert collected is not None
    assert collected[0].module_name == __name__.rpartition(".")[2]
    assert collected[0].area == "my/area"


@pytest.mark.parametrize("level", ["server", "provider"])
def test_an_unreadable_transform_fails_closed_with_a_warning(
    level: str, caplog: pytest.LogCaptureFixture
) -> None:
    """A transform whose rule is not data is refused, not read past.

    Publishing the pre-transform name documents an identity the server no
    longer serves; the mount path already refused, these levels did not.
    """
    from fastmcp.server.transforms import Transform

    class Prefix(Transform):
        async def list_tools(self, tools: t.Any) -> t.Any:
            return [
                tool.model_copy(update={"name": "public_" + tool.name})
                for tool in tools
            ]

    server: FastMCP = FastMCP("server")

    @server.tool
    def hello(a: int) -> str:
        """Hello."""
        return "ok"

    if level == "server":
        server.add_transform(Prefix())
    else:
        server.local_provider.add_transform(Prefix())

    with caplog.at_level(logging.WARNING):
        walked = _iter_components(server)

    assert walked == ()
    assert any("cannot reproduce" in rec.message for rec in caplog.records)


def test_a_registry_less_provider_under_a_namespace_is_named(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Namespacing a dynamic provider does not silence the diagnostic."""
    from fastmcp.server.providers.base import Provider

    class Dynamic(Provider):
        async def _list_tools(self) -> list[t.Any]:
            return []

    server: FastMCP = FastMCP("server")
    server.add_provider(Dynamic(), namespace="api")

    with caplog.at_level(logging.WARNING):
        assert _iter_components(server) == ()

    assert any("Dynamic" in rec.message for rec in caplog.records)
