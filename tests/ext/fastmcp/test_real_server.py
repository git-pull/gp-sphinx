"""Collector tests against a real FastMCP server.

The other tests build components from hand-written shims, which cannot
catch a rename in FastMCP's own object model: a stub keeps answering the
spelling it was written with. These build a real server instead, so an
SDK field rename fails here rather than silently emptying a docs page.

FastMCP is a dev-only dependency; the extension itself works without it.
"""

from __future__ import annotations

import typing as t
import warnings

import pytest

from sphinx_autodoc_fastmcp._collector import (
    _annotation_hints,
    _prompt_from_component,
    _resource_from_component,
    _tools_from_server,
)

pytest.importorskip("fastmcp")

from fastmcp import FastMCP  # noqa: E402
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
