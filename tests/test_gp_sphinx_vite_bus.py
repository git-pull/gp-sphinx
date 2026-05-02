"""Tests for :class:`gp_sphinx_vite.bus.AsyncioBus`.

Bus is the thread + event-loop bridge that lets Sphinx's sync hooks
drive ``ViteProcess``. Tests cover the lifecycle (start/stop/restart),
the two scheduling primitives (``call_sync`` / ``call_soon``), and a
few edge cases (call before start, double start, exceptions in
fire-and-forget coroutines).

Tests are intentionally synchronous (no ``@pytest.mark.asyncio``) — the
whole point of the bus is to run async code from a sync caller.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time

import pytest
from gp_sphinx_vite.bus import AsyncioBus


def test_start_makes_bus_running() -> None:
    """start() leaves the bus in a running state."""
    bus = AsyncioBus()
    try:
        assert not bus.is_running
        bus.start()
        assert bus.is_running
    finally:
        bus.stop()


def test_double_start_is_idempotent() -> None:
    """A second start() against an already-running bus is a no-op."""
    bus = AsyncioBus()
    try:
        bus.start()
        bus.start()  # must not raise / spawn a second thread
        assert bus.is_running
    finally:
        bus.stop()


def test_stop_before_start_is_idempotent() -> None:
    """stop() on a bus that was never started is a no-op."""
    bus = AsyncioBus()
    bus.stop()  # must not raise
    assert not bus.is_running


def test_call_sync_executes_coroutine_and_returns_result() -> None:
    """call_sync schedules a coroutine and blocks on its result."""

    async def _add(a: int, b: int) -> int:
        return a + b

    bus = AsyncioBus()
    try:
        bus.start()
        result = bus.call_sync(_add(2, 3))
    finally:
        bus.stop()
    assert result == 5


def test_call_sync_propagates_exceptions() -> None:
    """An exception in the coroutine surfaces in the caller's frame."""

    async def _boom() -> None:
        msg = "intentional"
        raise RuntimeError(msg)

    bus = AsyncioBus()
    try:
        bus.start()
        with pytest.raises(RuntimeError, match=r"intentional"):
            bus.call_sync(_boom())
    finally:
        bus.stop()


def test_call_sync_before_start_raises() -> None:
    """call_sync against an unstarted bus is a programming error."""
    bus = AsyncioBus()

    async def _noop() -> None:
        return None

    with pytest.raises(RuntimeError, match=r"call_sync.*before start"):
        bus.call_sync(_noop())


def test_call_soon_runs_coroutine_in_background() -> None:
    """call_soon schedules without blocking; the side effect lands eventually."""
    flag = threading.Event()

    async def _set_flag() -> None:
        flag.set()

    bus = AsyncioBus()
    try:
        bus.start()
        bus.call_soon(_set_flag())
        assert flag.wait(timeout=1.0)
    finally:
        bus.stop()


def test_call_soon_logs_exception_without_raising(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A background failure logs at ERROR but does not crash the bus."""

    async def _boom() -> None:
        msg = "background failure"
        raise RuntimeError(msg)

    flag = threading.Event()

    async def _flag_after() -> None:
        flag.set()

    bus = AsyncioBus()
    try:
        with caplog.at_level(logging.ERROR, logger="gp_sphinx_vite.bus"):
            bus.start()
            bus.call_soon(_boom())
            # Schedule a follow-up so we know the bus is still alive.
            bus.call_soon(_flag_after())
            assert flag.wait(timeout=1.0)
    finally:
        bus.stop()

    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert errors, "expected an ERROR log record from the failing coroutine"
    assert any("background coroutine" in r.getMessage() for r in errors)
    # The original exception is attached via exc_info — verify it.
    assert any(
        r.exc_info is not None
        and r.exc_info[1] is not None
        and "background failure" in str(r.exc_info[1])
        for r in errors
    )


def test_stop_cancels_pending_tasks() -> None:
    """In-flight long-running tasks are cancelled cleanly on stop()."""
    started = threading.Event()

    async def _hang() -> None:
        started.set()
        await asyncio.sleep(60)  # would outlast the test

    bus = AsyncioBus()
    bus.start()
    bus.call_soon(_hang())
    started.wait(timeout=1.0)

    t0 = time.monotonic()
    bus.stop(timeout=2.0)
    elapsed = time.monotonic() - t0
    assert not bus.is_running
    # Should return well under the 60-second sleep.
    assert elapsed < 2.0


def test_can_construct_a_new_bus_after_stop() -> None:
    """After stop(), a fresh AsyncioBus instance starts cleanly."""

    async def _ping() -> str:
        return "pong"

    first = AsyncioBus(name="first")
    first.start()
    first.stop()

    second = AsyncioBus(name="second")
    try:
        second.start()
        assert second.call_sync(_ping()) == "pong"
    finally:
        second.stop()
