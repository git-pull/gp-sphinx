"""Thread + asyncio event-loop bridge.

Sphinx's event hooks (``builder-inited``, ``build-finished``, …) are
synchronous callables. The orchestration logic that they drive is
asyncio-based (:class:`sphinx_vite_builder._internal.process.AsyncProcess`
uses ``asyncio.create_subprocess_exec``, pipe drainers, etc.). The bridge
between them is a *single* event loop running in a single daemon
thread, kept alive across ``builder-inited`` re-fires for
``sphinx-autobuild``.

Usage from a Sphinx hook:

.. code-block:: python

    bus = AsyncioBus()
    bus.start()
    bus.call_sync(some_coro())
    # ...
    bus.stop(timeout=5.0)

The bus has no Sphinx-specific knowledge; tests construct one and drive
it directly.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import typing as t

if t.TYPE_CHECKING:
    from collections.abc import Coroutine

logger = logging.getLogger(__name__)


class AsyncioBus:
    """A single asyncio event loop running in a daemon thread.

    Lifecycle:

    1. :meth:`start` spawns the thread; waits until the loop is ready.
    2. Hooks run :meth:`call_sync` (block on result) or :meth:`call_soon`
       (fire-and-forget).
    3. :meth:`stop` schedules the loop to stop, joins the thread.

    The bus is single-use. After ``stop()`` it is not safe to start
    again — construct a new instance.
    """

    def __init__(self, *, name: str = "sphinx-vite-builder-bus") -> None:
        self._name = name
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        # ``_stopped`` is set once a started bus has actually been torn
        # down. It enforces the class-level "single-use" contract from
        # ``start()``; a stop-before-start is a no-op and leaves this
        # ``False`` (the bus was never really live).
        self._stopped = False

    @property
    def is_running(self) -> bool:
        """True iff the loop thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the background event loop.

        Idempotent if the bus is already running; raises
        :class:`RuntimeError` if the bus has previously been stopped
        (the class is single-use, per the class docstring).
        """
        if self._stopped:
            msg = "AsyncioBus is single-use; construct a new instance after stop()"
            raise RuntimeError(msg)
        if self._thread is not None and self._thread.is_alive():
            return
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name=self._name,
        )
        self._thread.start()
        # Block until the loop has been assigned. Without this, a
        # call_sync() racing the thread startup would deref None.
        self._ready.wait()

    def call_sync(
        self,
        coro: Coroutine[t.Any, t.Any, t.Any],
        *,
        timeout: float | None = None,
    ) -> t.Any:
        """Schedule ``coro`` on the loop and block on its result.

        Parameters
        ----------
        coro
            The coroutine object (call-but-don't-await first).
        timeout
            Forwarded to ``concurrent.futures.Future.result``. ``None``
            blocks indefinitely.

        Raises
        ------
        RuntimeError
            If the bus is not running.
        """
        if self._loop is None:
            # Close the coroutine before raising so we don't leak a
            # "coroutine was never awaited" warning at gc time.
            coro.close()
            msg = "AsyncioBus.call_sync() called before start()"
            raise RuntimeError(msg)
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def call_soon(
        self,
        coro: Coroutine[t.Any, t.Any, t.Any],
    ) -> None:
        """Schedule ``coro`` and return immediately. Errors go to the bus logger."""
        if self._loop is None:
            coro.close()
            msg = "AsyncioBus.call_soon() called before start()"
            raise RuntimeError(msg)
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        def _log_exception(fut: t.Any) -> None:
            exc = fut.exception()
            if exc is not None:
                logger.error(
                    "background coroutine on %s raised",
                    self._name,
                    exc_info=exc,
                )

        future.add_done_callback(_log_exception)

    def stop(self, *, timeout: float = 5.0) -> None:
        """Stop the loop and join the thread. Idempotent.

        Once a started bus has been stopped, ``_stopped`` is set so a
        subsequent ``start()`` on the same instance raises rather than
        silently re-spawning. A stop-before-start is a no-op and leaves
        ``_stopped`` unchanged.
        """
        if self._loop is None or self._thread is None:
            return
        if not self._thread.is_alive():
            self._thread = None
            self._loop = None
            self._stopped = True
            return

        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            logger.warning(
                "%s thread did not exit within %.1fs of loop.stop()",
                self._name,
                timeout,
            )
        self._thread = None
        self._loop = None
        self._stopped = True

    def _run(self) -> None:
        """Thread target: own and run the loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        try:
            loop.run_forever()
        finally:
            try:
                # Cancel any remaining tasks so they don't leak past
                # the loop's death.
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True),
                    )
            finally:
                loop.close()
