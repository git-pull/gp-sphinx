"""Synthetic FastMCP server for the documentation page live demos.

Companion to :mod:`fastmcp_demo_tools`, which supplies the tool cards. This
module supplies what only a live server can: resources, resource templates and
prompts, read off the running instance rather than replayed through a
hand-written collector.

It registers no tools, so tool collection still falls through to
``fastmcp_tool_modules`` and the demo tool cards keep rendering.

Examples
--------
>>> mcp.name
'gp-sphinx-demo'
>>> changelog_entry.__doc__.splitlines()[0]
'One changelog entry, as Markdown.'
"""

from __future__ import annotations

from fastmcp import FastMCP
from mcp.types import Annotations

mcp: FastMCP = FastMCP("gp-sphinx-demo")


@mcp.resource(
    "docs://changelog",
    mime_type="text/markdown",
    annotations=Annotations(
        audience=["user"],
        priority=0.8,
        last_modified="2026-09-05T00:00:00Z",
    ),
)
def changelog() -> str:
    """Return the project changelog, as Markdown.

    Carries every annotation a resource can set, so the card renders a
    complete facts row.

    Returns
    -------
    str
        Changelog body.
    """
    return "# Changelog\n"


@mcp.resource("docs://readme", mime_type="text/markdown")
def readme() -> str:
    """Return the project README, as Markdown.

    Sets no annotations, so the card shows its MIME type alone — annotation
    facts appear only when set.

    Returns
    -------
    str
        README body.
    """
    return "# gp-sphinx\n"


@mcp.resource("docs://changelog/{version}", mime_type="text/markdown")
def changelog_entry(version: str) -> str:
    """One changelog entry, as Markdown.

    Parameters
    ----------
    version : str
        Release to fetch, such as ``0.1.0a38``.

    Returns
    -------
    str
        Entry body.
    """
    return f"## {version}\n"


@mcp.prompt
def summarize_release(version: str, audience: str) -> str:
    """Draft a release summary for one version.

    Parameters
    ----------
    version : str
        Release to summarize.
    audience : str
        Who the summary is written for.

    Returns
    -------
    str
        Prompt text.
    """
    return f"Summarize {version} for {audience}."
