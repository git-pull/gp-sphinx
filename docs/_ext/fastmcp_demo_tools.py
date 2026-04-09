"""Synthetic FastMCP tools for the documentation page live demos.

Examples
--------
>>> list_sessions("prod")
['prod:0', 'prod:1']
>>> create_session("demo")["name"]
'demo'
>>> delete_session("old-session")
True
"""

from __future__ import annotations

import types
import typing as t


def list_sessions(server: str, limit: int = 20) -> list[str]:
    """List active sessions for one server.

    Parameters
    ----------
    server : str
        Server name to inspect.
    limit : int
        Maximum number of sessions to return.

    Returns
    -------
    list[str]
        Session identifiers for the server.

    Examples
    --------
    >>> list_sessions("prod")
    ['prod:0', 'prod:1']
    """
    return [f"{server}:{index}" for index in range(min(limit, 2))]


t.cast(t.Any, list_sessions).__fastmcp__ = types.SimpleNamespace(
    name="list_sessions", title="List Sessions", tags={"readonly"}, annotations=None
)


def create_session(
    name: str,
    window_count: int = 1,
    detached: bool = False,
) -> dict[str, str | int | bool]:
    """Create one session and return the created record.

    Parameters
    ----------
    name : str
        Session name to create.
    window_count : int
        Initial number of windows.
    detached : bool
        Whether to create the session detached from the current client.

    Returns
    -------
    dict[str, str | int | bool]
        Created session metadata.

    Examples
    --------
    >>> create_session("demo")
    {'name': 'demo', 'windows': 1, 'detached': False}
    """
    return {
        "name": name,
        "windows": window_count,
        "detached": detached,
    }


t.cast(t.Any, create_session).__fastmcp__ = types.SimpleNamespace(
    name="create_session", title="Create Session", tags={"mutating"}, annotations=None
)


def delete_session(name: str, force: bool = False) -> bool:
    """Delete one session from the server.

    Parameters
    ----------
    name : str
        Session name to delete.
    force : bool
        Whether to skip confirmation checks.

    Returns
    -------
    bool
        ``True`` when the session was removed.

    Examples
    --------
    >>> delete_session("old-session")
    True
    """
    return True


t.cast(t.Any, delete_session).__fastmcp__ = types.SimpleNamespace(
    name="delete_session",
    title="Delete Session",
    tags={"destructive"},
    annotations=None,
)
