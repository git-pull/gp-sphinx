"""Demo module for sphinx-autodoc-typehints-gp showcase.

Exercises every rendering improvement landed on the
``improved-defaults-reprs`` branch — source-text defaults, dataclass
factory rendering, long-data truncation, cross-referenced default
values, field-list xref styling, and the prefix monospace wrapper.
Each documented object below is referenced from
``docs/packages/sphinx-autodoc-typehints-gp/examples.md`` so the HTML
output renders with all transforms active.
"""

from __future__ import annotations

import dataclasses
import enum


class CacheScope(enum.Enum):
    """Where a cached entry lives in the storage hierarchy."""

    Process = "process"
    Session = "session"
    Global = "global"


class _DefaultRetry:
    """Sentinel type for the ``retry=`` parameter's default value."""


DEFAULT_RETRY: _DefaultRetry = _DefaultRetry()
"""Sentinel default for ``retry=`` parameters on connection helpers.

When ``retry is DEFAULT_RETRY`` the helper picks a transport-aware
retry policy from the bound transport's ``retry_policy`` attribute.
"""


SHORT_DEFAULT: str = "admin"
"""A short, readable module-level constant — renders as-is."""


LONG_DEFAULT_RULES: list[tuple[str, str]] = [
    (f"rule-{i:02d}", f"description for rule number {i}") for i in range(20)
]
"""A long ``list[tuple[str, str]]`` used as a documented constant.

The ``repr()`` exceeds the 200-char threshold so the rendered
``:value:`` collapses to ``<...truncated, N chars>`` instead of
sprawling across the page.
"""


class ConnectionFailure(Exception):
    """Raised when a connection attempt fails after exhausting retries."""


class Transport:
    """Documented internal transport — referenced as a parameter type."""


@dataclasses.dataclass
class HookCounters:
    """Dataclass exercising every default-factory shape.

    Each field uses ``field(default_factory=...)`` with a stdlib
    container type or a custom callable. After the synthetic-init
    listener runs, the rendered ``__init__`` signature shows the
    factory call source text instead of ``=<factory>``.
    """

    alerts: list[str] = dataclasses.field(default_factory=list)
    index: dict[str, int] = dataclasses.field(default_factory=dict)
    names: set[str] = dataclasses.field(default_factory=set)
    tags: tuple[str, ...] = dataclasses.field(default_factory=tuple)
    transports: list[Transport] = dataclasses.field(default_factory=list)


def open_session(
    transport: Transport,
    *,
    scope: CacheScope = CacheScope.Session,
    retry: _DefaultRetry = DEFAULT_RETRY,
    label: str = "default",
) -> Transport:
    """Open a session against *transport*.

    The ``scope`` and ``retry`` defaults both reference documented
    targets on this same page; Stage C's xref transform turns each
    documented identifier inside a default-value span into a
    clickable cross-reference using the canonical
    ``:py:obj:``-styled HTML shape (``<a class="reference internal"
    href="…"><code class="xref py py-obj">…</code></a>``).

    Parameters
    ----------
    transport : Transport
        The documented transport instance.
    scope : CacheScope
        Scope at which session state is cached.
    retry : _DefaultRetry
        Retry sentinel; pass an explicit policy to override.
    label : str
        Optional label propagated to log records.

    Returns
    -------
    Transport
        The same transport, now bound to the session.

    Raises
    ------
    ConnectionFailure
        Raised when the transport cannot be opened after the retry
        policy is exhausted.
    """
    return transport


def with_lambda_default(callback: object = lambda: None) -> None:
    """Demonstrate Stage C's plain-text fallback for lambda defaults.

    ``ast.parse`` of the default succeeds but the lambda branch isn't
    handled by the xref transform; the rendered default sits as plain
    text inside the ``default_value`` span (no spurious ``<code
    class="xref">`` styling that would imply a missing link target).
    """
    del callback
