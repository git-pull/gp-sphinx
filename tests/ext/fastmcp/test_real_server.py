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
import pathlib
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
    _strip_schema_note,
    _tool_from_component,
    _tools_from_server,
    collect_tools,
)

pytest.importorskip("fastmcp")

from fastmcp import Context, FastMCP  # noqa: E402
from fastmcp.prompts import Prompt as _Prompt  # noqa: E402
from fastmcp.resources import (
    Resource as _Resource,  # noqa: E402
    ResourceTemplate as _ResourceTemplate,  # noqa: E402
)
from fastmcp.tools import Tool as _Tool  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from typing_extensions import TypedDict  # noqa: E402


class _Boxed(TypedDict):
    """An object whose only field is named like a generated wrapper's.

    ``typing_extensions`` rather than ``typing``: pydantic rejects
    ``typing.TypedDict`` below Python 3.12.
    """

    result: int


class _Point(BaseModel):
    """A coordinate accepted by a tool."""

    #: Horizontal coordinate.
    x: int


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
def test_a_custom_transform_is_documented_as_served(level: str) -> None:
    """A transform whose rule is not data still documents the served name.

    Listing through FastMCP's own ``Provider.list_*`` applies every
    transform the way the server does, so nothing has to be reproduced.
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

    assert sorted(
        tool.name for tool in _iter_components(server) if isinstance(tool, _Tool)
    ) == sorted(
        tool.name for tool in asyncio.run(server.list_tools(run_middleware=False))
    )


@pytest.mark.parametrize("namespace", [None, "api"])
def test_a_dynamic_provider_is_documented(namespace: str | None) -> None:
    """A provider that lists only asynchronously is still collected."""
    from fastmcp.server.providers.base import Provider

    class Dynamic(Provider):
        async def _list_tools(self) -> list[t.Any]:
            return [_Tool.from_function(lambda a: "ok", name="dyn_tool")]

    server: FastMCP = FastMCP("server")
    if namespace is None:
        server.add_provider(Dynamic())
    else:
        server.add_provider(Dynamic(), namespace=namespace)

    assert sorted(
        tool.name for tool in _iter_components(server) if isinstance(tool, _Tool)
    ) == sorted(
        tool.name for tool in asyncio.run(server.list_tools(run_middleware=False))
    )


def test_a_disabled_tool_stays_in_its_documentation() -> None:
    """A tool switched off at runtime is documented anyway.

    ``FastMCP.list_tools`` drops it even with middleware off; the
    provider-level listing does not, and the docs describe what the server
    can serve.
    """
    server: FastMCP = FastMCP("server")

    @server.tool
    def visible(a: int) -> str:
        """Visible."""
        return "ok"

    @server.tool
    def hidden(a: int) -> str:
        """Hidden."""
        return "ok"

    server.disable(keys={"tool:hidden@"})

    assert "hidden" not in {
        tool.name for tool in asyncio.run(server.list_tools(run_middleware=False))
    }
    assert sorted(
        tool.name for tool in _iter_components(server) if isinstance(tool, _Tool)
    ) == ["hidden", "visible"]


def test_a_disabled_tool_inside_a_mount_stays_documented() -> None:
    """Disabling reaches into a mounted child, and documentation does not.

    ``FastMCPProvider`` lists its child through the child's own
    ``list_tools()``, which drops disabled components and runs the child's
    middleware, so a tool switched off or gated inside a mounted server
    vanished from the docs.
    """
    child: FastMCP = FastMCP("child")

    @child.tool
    def visible(a: int) -> str:
        """Visible."""
        return "ok"

    @child.tool
    def hidden(a: int) -> str:
        """Hidden."""
        return "ok"

    child.disable(keys={"tool:hidden@"})
    parent: FastMCP = FastMCP("parent")
    parent.mount(child, namespace="ns")

    assert "ns_hidden" not in {
        tool.name for tool in asyncio.run(parent.list_tools(run_middleware=False))
    }
    assert sorted(
        tool.name for tool in _iter_components(parent) if isinstance(tool, _Tool)
    ) == ["ns_hidden", "ns_visible"]


def test_a_namespaced_tool_resolves_past_a_decoy_sibling() -> None:
    """A sibling literally named ``namespace_name`` is not the origin.

    Recovering the original by stripping the namespace off the served name
    matches the decoy, and documents its description and types.
    """
    child: FastMCP = FastMCP("child")

    @child.tool
    def hello(x: int) -> str:
        """Real hello."""
        return "ok"

    @child.tool
    def ns_hello(x: str) -> str:
        """Decoy."""
        return "ok"

    parent: FastMCP = FastMCP("parent")
    parent.mount(child, namespace="ns")

    collected = _tools_from_server(parent, area_map={}, axes=())
    assert collected is not None
    documented = {info.name: info for info in collected}
    assert documented["ns_hello"].docstring == "Real hello."
    assert [p.type_str for p in documented["ns_hello"].params] == ["int"]
    assert documented["ns_ns_hello"].docstring == "Decoy."


def test_a_transformed_argument_documents_its_served_type() -> None:
    """A transform that retypes an argument owns the displayed type.

    The tool it was made from still says ``int``; the server publishes
    ``string``, and the docs describe what a caller may send.
    """
    from fastmcp.tools.tool_transform import ArgTransform

    def square(x: int) -> int:
        """Square."""
        return x * x

    transformed = _Tool.from_tool(
        _Tool.from_function(square),
        name="square_str",
        transform_args={"x": ArgTransform(type=str)},
    )
    server: FastMCP = FastMCP("server")
    server.add_tool(transformed)

    collected = _tools_from_server(server, area_map={}, axes=())
    assert collected is not None
    assert [(p.name, p.type_str) for p in collected[0].params] == [("x", "string")]


def test_one_failing_provider_does_not_abort_the_build(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An unreachable provider is logged and skipped, not raised.

    FastMCP's aggregate defaults to ``provider_error_strategy="warn"`` and
    still serves its healthy providers; letting the failure escape aborts
    ``builder-inited`` and produces no documentation at all.
    """
    from fastmcp.server.providers.base import Provider

    class Broken(Provider):
        async def _list_tools(self) -> list[t.Any]:
            msg = "remote unavailable"
            raise OSError(msg)

    server: FastMCP = FastMCP("server")

    @server.tool
    def local(a: int) -> str:
        """Local."""
        return "ok"

    server.add_provider(Broken())

    with caplog.at_level(logging.WARNING):
        collected = [
            tool.name for tool in _iter_components(server) if isinstance(tool, _Tool)
        ]

    assert collected == ["local"]
    assert any("Broken" in rec.message for rec in caplog.records)


def test_a_configured_raise_strategy_is_honoured() -> None:
    """``provider_error_strategy="raise"`` still fails the collection."""
    from fastmcp.server.providers.base import Provider

    class Broken(Provider):
        async def _list_tools(self) -> list[t.Any]:
            msg = "remote unavailable"
            raise OSError(msg)

    server: FastMCP = FastMCP("server")
    server.add_provider(Broken())
    server.provider_error_strategy = "raise"

    with pytest.raises(OSError, match="remote unavailable"):
        _iter_components(server)


def test_an_aggregate_provider_is_traversed_not_asked() -> None:
    """A mount wrapped in an aggregate keeps its disabled components.

    An aggregate holds providers of its own; asking it to list re-enters
    each child's filtered listing.
    """
    from fastmcp.server.providers.aggregate import AggregateProvider
    from fastmcp.server.providers.fastmcp_provider import FastMCPProvider

    child: FastMCP = FastMCP("child")

    @child.tool
    def visible(a: int) -> str:
        """Visible."""
        return "ok"

    @child.tool
    def hidden(a: int) -> str:
        """Hidden."""
        return "ok"

    child.disable(keys={"tool:hidden@"})
    server: FastMCP = FastMCP("server")
    server.add_provider(AggregateProvider([FastMCPProvider(child)]))

    assert sorted(
        tool.name for tool in _iter_components(server) if isinstance(tool, _Tool)
    ) == ["hidden", "visible"]


def test_a_published_description_outranks_the_docstring() -> None:
    """``description=`` is what the server tells a caller."""
    server: FastMCP = FastMCP("server")

    @server.tool(description="Published description.")
    def both(a: int) -> str:
        """Docstring text."""
        return "ok"

    @server.tool
    def only_doc(a: int) -> str:
        """Only a docstring."""
        return "ok"

    collected = _tools_from_server(server, area_map={}, axes=())
    assert collected is not None
    documented = {info.name: info.docstring for info in collected}
    assert documented["both"] == "Published description."
    assert documented["only_doc"] == "Only a docstring."


def test_a_slow_provider_is_skipped_like_a_failing_one(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A provider that hangs does not hold the build hostage.

    Bounding the whole listing raises in the Sphinx thread, outside the
    per-provider failure policy, so a slow remote aborted collection even
    under ``provider_error_strategy="warn"``.
    """
    from fastmcp.server.providers.base import Provider

    from sphinx_autodoc_fastmcp import _collector

    class Slow(Provider):
        async def _list_tools(self) -> list[t.Any]:
            await asyncio.sleep(30)
            return []

    monkeypatch.setattr(_collector, "_PROVIDER_TIMEOUT", 0.5)
    server: FastMCP = FastMCP("server")

    @server.tool
    def local(a: int) -> str:
        """Local."""
        return "ok"

    server.add_provider(Slow())

    with caplog.at_level(logging.WARNING):
        collected = [
            tool.name for tool in _iter_components(server) if isinstance(tool, _Tool)
        ]

    assert collected == ["local"]
    assert any("Slow" in rec.message for rec in caplog.records)


def test_an_authored_schema_request_is_not_stripped() -> None:
    """Only FastMCP's generated instruction is removed.

    Both spellings say "matching the following"; an author asking for a
    schema does not, and their guidance is the whole description.
    """
    authored = 'Provide a JSON schema: {"type": "object"}.'

    assert _strip_schema_note(authored) == authored
    assert _strip_schema_note(f"Summary.\n\n{authored}") == f"Summary.\n\n{authored}"
    assert (
        _strip_schema_note(
            "Summary.\n\nProvide a value matching the following JSON schema: "
            '{"type":"number"}. Encode non-string values as JSON.'
        )
        == "Summary."
    )


def test_a_renamed_tool_keeps_its_return_information() -> None:
    """A rename leaves the return contract intact, so the docs should too.

    The forwarding callable carries no annotation; the published output
    schema still describes the result.
    """
    from fastmcp.server.transforms import ToolTransform
    from fastmcp.tools.tool_transform import ToolTransformConfig

    server: FastMCP = FastMCP("server")

    @server.tool
    def counts(a: int) -> int:
        """Counts."""
        return 1

    server.local_provider.add_transform(
        ToolTransform({"counts": ToolTransformConfig(name="renamed")})
    )

    collected = _tools_from_server(server, area_map={}, axes=())
    assert collected is not None
    assert collected[0].name == "renamed"
    assert collected[0].return_annotation == "integer"


def _identity(component: t.Any) -> str:
    """The name or URI a component is served under."""
    return str(
        getattr(component, "uri", None)
        or getattr(component, "uri_template", None)
        or component.name
    )


def _matrix_leaf() -> FastMCP:
    """A server carrying one component of every kind."""
    server: FastMCP = FastMCP("leaf")

    @server.tool
    def alpha(a: int) -> str:
        """Alpha."""
        return "ok"

    @server.resource("data://thing")
    def thing() -> str:
        """Thing."""
        return "{}"

    @server.resource("data://item/{x}")
    def item(x: str) -> str:
        """Item."""
        return "{}"

    @server.prompt
    def draft(topic: str) -> str:
        """Draft."""
        return "drafted"

    return server


def _attach(shape: str, parent: FastMCP, child: FastMCP, index: int) -> None:
    """Attach ``child`` to ``parent`` the way ``shape`` names."""
    from fastmcp.server.providers.aggregate import AggregateProvider
    from fastmcp.server.providers.fastmcp_provider import FastMCPProvider
    from fastmcp.server.transforms import Namespace

    namespace = f"n{index}"
    if shape == "mount":
        parent.mount(child)
    elif shape == "mount+ns":
        parent.mount(child, namespace=namespace)
    elif shape == "add_provider":
        parent.add_provider(FastMCPProvider(child))
    elif shape == "add_provider+ns":
        parent.add_provider(FastMCPProvider(child), namespace=namespace)
    elif shape == "aggregate":
        parent.add_provider(AggregateProvider([FastMCPProvider(child)]))
    elif shape == "aggregate+ns":
        parent.add_provider(
            AggregateProvider([FastMCPProvider(child)]), namespace=namespace
        )
    elif shape == "child-transform":
        child.add_transform(Namespace(f"x{index}"))
        parent.mount(child)
    else:  # pragma: no cover - guards a typo in the parametrization
        msg = f"unknown attachment shape {shape!r}"
        raise AssertionError(msg)


#: Every way a server can carry another server's components. Each round of
#: review has found a defect on a shape the previous matrix did not vary, so
#: the axis is the attachment itself, not one example of it.
_ATTACHMENTS = (
    "mount",
    "mount+ns",
    "add_provider",
    "add_provider+ns",
    "aggregate",
    "aggregate+ns",
    "child-transform",
)

_KINDS = {
    "tools": "list_tools",
    "resources": "list_resources",
    "resource_templates": "list_resource_templates",
    "prompts": "list_prompts",
}


@pytest.mark.parametrize("shape", _ATTACHMENTS)
@pytest.mark.parametrize("depth", [1, 2])
def test_collected_identity_equals_served_identity(shape: str, depth: int) -> None:
    """Every component is documented under the identity the server serves.

    The matrix varies how a child is attached and how deeply, because a
    rename applies differently at each boundary and the collector has to
    arrive at the same answer the server does.
    """
    server = _matrix_leaf()
    for index in range(depth):
        parent: FastMCP = FastMCP(f"level{index}")
        _attach(shape, parent, server, index)
        server = parent

    walked = _iter_components(server)
    for kind, method in _KINDS.items():
        served = asyncio.run(getattr(server, method)(run_middleware=False))
        cls = {
            "tools": _Tool,
            "resources": _Resource,
            "resource_templates": _ResourceTemplate,
            "prompts": _Prompt,
        }[kind]
        assert sorted(_identity(c) for c in walked if isinstance(c, cls)) == sorted(
            _identity(c) for c in served
        ), kind


@pytest.mark.parametrize("shape", _ATTACHMENTS)
def test_a_disabled_tool_survives_every_attachment(shape: str) -> None:
    """Documentation describes what a server can serve, at every boundary.

    Each attachment reaches its child differently, and one of them listed
    through the child's own filtered listing.
    """
    child = _matrix_leaf()
    child.disable(keys={"tool:alpha@"})
    parent: FastMCP = FastMCP("parent")
    _attach(shape, parent, child, 0)

    names = [tool.name for tool in _iter_components(parent) if isinstance(tool, _Tool)]
    assert any(name.endswith("alpha") for name in names), names


def test_a_slow_provider_does_not_erase_its_healthy_siblings(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The bound sits on the leaf that lists, not on a subtree.

    Bounding a mounted child as a whole discards the components already
    gathered beneath it, so one slow descendant emptied the mount.
    """
    from fastmcp.server.providers.base import Provider

    from sphinx_autodoc_fastmcp import _collector

    class Slow(Provider):
        async def _list_tools(self) -> list[t.Any]:
            await asyncio.sleep(30)
            return []

    monkeypatch.setattr(_collector, "_PROVIDER_TIMEOUT", 0.5)
    child: FastMCP = FastMCP("child")

    @child.tool
    def local(a: int) -> str:
        """Local."""
        return "ok"

    child.add_provider(Slow())
    parent: FastMCP = FastMCP("parent")
    parent.mount(child, namespace="ns")

    with caplog.at_level(logging.WARNING):
        collected = [
            tool.name for tool in _iter_components(parent) if isinstance(tool, _Tool)
        ]

    assert collected == ["ns_local"]


def test_an_alias_is_resolved_to_the_parameter_that_declares_it() -> None:
    """A published alias may be another parameter's own name.

    Looking the published name up in the signature then borrows the wrong
    annotation, and the table contradicts what the server accepts.
    """
    server: FastMCP = FastMCP("server")

    @server.tool
    def query(
        foo: t.Annotated[int, Field(alias="bar")] = 1,
        bar: t.Annotated[str, Field(alias="baz")] = "x",
    ) -> str:
        """Query."""
        return "ok"

    collected = _tools_from_server(server, area_map={}, axes=())
    assert collected is not None
    assert [(p.name, p.type_str) for p in collected[0].params] == [
        ("bar", "int"),
        ("baz", "str"),
    ]


def test_only_a_marked_wrapper_is_unwrapped() -> None:
    """A TypedDict whose only field is ``result`` is not a wrapper.

    It publishes the same shape as one FastMCP generated, so the marker is
    what distinguishes them.
    """
    from fastmcp.server.transforms import ToolTransform
    from fastmcp.tools.tool_transform import ToolTransformConfig

    boxed_server: FastMCP = FastMCP("boxed")

    @boxed_server.tool
    def boxed(a: int) -> _Boxed:
        """Boxed."""
        return {"result": 1}

    boxed_server.local_provider.add_transform(
        ToolTransform({"boxed": ToolTransformConfig(name="renamed")})
    )

    plain_server: FastMCP = FastMCP("plain")

    @plain_server.tool
    def counts(a: int) -> int:
        """Counts."""
        return 1

    plain_server.local_provider.add_transform(
        ToolTransform({"counts": ToolTransformConfig(name="also_renamed")})
    )

    boxed_collected = _tools_from_server(boxed_server, area_map={}, axes=())
    plain_collected = _tools_from_server(plain_server, area_map={}, axes=())
    assert boxed_collected is not None
    assert plain_collected is not None
    assert boxed_collected[0].return_annotation == "object"
    assert plain_collected[0].return_annotation == "integer"


def test_an_alias_declared_in_a_default_is_resolved() -> None:
    """A ``Field`` may be the default rather than ``Annotated`` metadata.

    Both spellings publish the alias, and reading only one of them borrows
    the other parameter's annotation.
    """
    server: FastMCP = FastMCP("server")

    @server.tool
    def query(
        foo: int = Field(1, alias="bar"),
        bar: str = Field("x", alias="baz"),
    ) -> str:
        """Query."""
        return "ok"

    collected = _tools_from_server(server, area_map={}, axes=())
    assert collected is not None
    assert [(p.name, p.type_str) for p in collected[0].params] == [
        ("bar", "int"),
        ("baz", "str"),
    ]


def test_a_stalled_transform_does_not_block_the_build(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A transform is as able to stall as the listing it wraps.

    ``_PROVIDER_TIMEOUT`` bounded only the underlying ``_list_*`` call, so a
    transform that never returns held the build open indefinitely.
    """
    from fastmcp.server.transforms import Transform

    from sphinx_autodoc_fastmcp import _collector

    class Stalled(Transform):
        async def list_tools(self, tools: t.Any) -> t.Any:
            await asyncio.sleep(30)
            return tools

    monkeypatch.setattr(_collector, "_PROVIDER_TIMEOUT", 0.5)
    server: FastMCP = FastMCP("server")

    @server.tool
    def local(a: int) -> str:
        """Local."""
        return "ok"

    server.local_provider.add_transform(Stalled())

    with caplog.at_level(logging.WARNING):
        collected = [
            tool.name for tool in _iter_components(server) if isinstance(tool, _Tool)
        ]

    assert collected == []
    assert any("failed to list" in rec.message for rec in caplog.records)


def test_renamed_model_parameters_resolve_schema_references() -> None:
    """Forwarding functions retain named model types and nullable unions."""
    from fastmcp.server.transforms import ToolTransform
    from fastmcp.tools.tool_transform import ToolTransformConfig

    server: FastMCP = FastMCP("models")

    @server.tool
    def locate(point: _Point, maybe: _Point | None) -> _Point:
        """Locate a point."""
        return point

    server.add_transform(ToolTransform({"locate": ToolTransformConfig(name="lookup")}))
    collected = _tools_from_server(server, area_map={}, axes=())
    assert collected is not None
    assert [(p.name, p.type_str) for p in collected[0].params] == [
        ("point", "object"),
        ("maybe", "object | null"),
    ]


@pytest.mark.parametrize(
    ("prop", "expected"),
    [
        ({"$ref": "#/$defs/a~1b~0c"}, "integer"),
        ({"oneOf": [{"$ref": "#/$defs/a~1b~0c"}, {"type": "null"}]}, "integer | null"),
        ({"$ref": "#/$defs/cycle"}, ""),
        ({"$ref": "#/$defs/missing"}, ""),
    ],
)
def test_schema_references_are_local_and_cycle_safe(
    prop: dict[str, t.Any], expected: str
) -> None:
    """Resolve JSON pointers without following missing or recursive targets."""
    schema = {
        "$defs": {
            "a/b~c": {"type": "integer"},
            "cycle": {"$ref": "#/$defs/cycle"},
        }
    }
    assert _schema_type_text(prop, schema) == expected


def test_skill_discovery_refreshes_during_collection(tmp_path: pathlib.Path) -> None:
    """Skills added after provider construction appear without a live listing."""
    from fastmcp.server.providers.skills import SkillsDirectoryProvider

    provider = SkillsDirectoryProvider(tmp_path, reload=True)
    server: FastMCP = FastMCP("skills")
    server.add_provider(provider, namespace="api")
    skill = tmp_path / "fresh"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: fresh\ndescription: Fresh skill\n---\n\nRead this skill.\n"
    )

    collected = list(_iter_components(server))
    served = asyncio.run(server.list_resources())
    templates = asyncio.run(server.list_resource_templates())
    assert served
    assert templates
    assert sorted(str(c.uri) for c in collected if isinstance(c, _Resource)) == sorted(
        str(c.uri) for c in served
    )
    assert sorted(
        c.uri_template for c in collected if isinstance(c, _ResourceTemplate)
    ) == sorted(c.uri_template for c in templates)


def test_validation_alias_owns_the_published_input() -> None:
    """Input aliases take precedence over serialization aliases."""
    server: FastMCP = FastMCP("aliases")

    @server.tool
    def annotated(
        foo: t.Annotated[int, Field(alias="other", validation_alias="bar")],
        bar: t.Annotated[str, Field(alias="baz")],
    ) -> None:
        """Accept aliased inputs."""

    @server.tool
    def defaults(
        foo: int = Field(1, alias="other", validation_alias="bar"),
        bar: str = Field("x", alias="baz"),
    ) -> None:
        """Accept aliased defaults."""

    collected = _tools_from_server(server, area_map={}, axes=())
    assert collected is not None
    for tool in collected:
        assert [(p.name, p.type_str) for p in tool.params] == [
            ("bar", "int"),
            ("baz", "str"),
        ]
