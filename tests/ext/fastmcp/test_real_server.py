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
    _prompt_from_component,
    _resource_from_component,
    _tool_from_component,
    _tools_from_server,
)

pytest.importorskip("fastmcp")

from fastmcp import Context, FastMCP  # noqa: E402
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
