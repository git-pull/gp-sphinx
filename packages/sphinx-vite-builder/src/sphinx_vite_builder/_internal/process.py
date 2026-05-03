"""Async subprocess wrapper used by the Vite/pnpm orchestration.

Wraps :func:`asyncio.create_subprocess_exec` with the conventions the
backend and extension heads need:

- ``stdout`` / ``stderr`` are piped through line-buffered drainers that
  prefix each line with a label and route it to a
  :class:`logging.Logger` — info for stdout, warning for stderr.
- ``PYTHONUNBUFFERED=1`` is forced into the child env so Python tools
  invoked via the package-manager bridge don't withhold their output.
- On POSIX, the child runs in a new session (``start_new_session=True``)
  so ``SIGTERM`` cleanly takes down the entire process tree (``pnpm exec``
  shells out to multiple intermediate processes — without session
  isolation, only the top-level pnpm wrapper would exit).
- :meth:`AsyncProcess.terminate` is graceful-then-forceful: SIGTERM,
  await up to ``timeout`` seconds, escalate to SIGKILL if the child is
  still alive. Idempotent: calling on an already-exited process is a
  no-op.

Argument lists are passed directly to the asyncio subprocess primitive;
no shell, no string interpolation, no command-injection surface.

The class is intentionally generic over "what command to run" so the
same wrapper covers the production vite / pnpm calls and the fake
shell scripts used in tests.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import pathlib
import sys
import typing as t

if t.TYPE_CHECKING:
    pass

_module_logger = logging.getLogger(__name__)


class AsyncProcess:
    """Async wrapper around a subprocess (one-shot or long-running).

    Used for both ``pnpm install`` (one-shot, awaited) and
    ``pnpm exec vite build --watch`` (long-running, terminated on
    teardown).
    """

    def __init__(
        self,
        *,
        label: str = "subprocess",
        logger: logging.Logger | logging.LoggerAdapter[t.Any] | None = None,
    ) -> None:
        # Accepts either a stdlib Logger or a LoggerAdapter (Sphinx's
        # ``sphinx.util.logging.SphinxLoggerAdapter`` is a LoggerAdapter
        # subclass). Both expose the .log() method the drainers use.
        self._label = label
        self._logger: logging.Logger | logging.LoggerAdapter[t.Any] = (
            logger if logger is not None else _module_logger
        )
        self._process: asyncio.subprocess.Process | None = None
        self._drainers: list[asyncio.Task[None]] = []
        self._stderr_buffer: list[str] = []

    @property
    def is_running(self) -> bool:
        """True iff the child has been started and has not yet exited."""
        return self._process is not None and self._process.returncode is None

    @property
    def returncode(self) -> int | None:
        """Process exit code, or ``None`` if the child hasn't exited (yet)."""
        return self._process.returncode if self._process is not None else None

    @property
    def pid(self) -> int | None:
        """Child process ID, or ``None`` if not started."""
        return self._process.pid if self._process is not None else None

    @property
    def captured_stderr(self) -> str:
        """Joined stderr lines captured by the drainer.

        Useful for surfacing the underlying tool's diagnostic in error
        messages when a build fails.
        """
        return "\n".join(self._stderr_buffer)

    async def start(
        self,
        command: t.Sequence[str],
        *,
        cwd: pathlib.Path,
        env: t.Mapping[str, str] | None = None,
    ) -> None:
        """Spawn ``command`` and start draining its stdout / stderr.

        Parameters
        ----------
        command
            Argument list. Passed straight to the asyncio subprocess
            primitive; no shell.
        cwd
            Working directory for the child.
        env
            Optional environment override. ``PYTHONUNBUFFERED=1`` is
            always injected on top of whatever this provides (or, if
            ``None``, on top of :data:`os.environ`).

        Raises
        ------
        RuntimeError
            If :meth:`start` is called twice on the same instance
            without an intervening :meth:`terminate`.
        """
        if self._process is not None:
            msg = "AsyncProcess.start() called twice; spawn a new instance instead"
            raise RuntimeError(msg)

        merged_env = dict(env) if env is not None else dict(os.environ)
        merged_env["PYTHONUNBUFFERED"] = "1"

        # POSIX-only: ``start_new_session`` puts the child in its own
        # session/process group so SIGTERM to that group takes down
        # ``pnpm exec`` plus all its descendants. On Windows there's no
        # equivalent; the asyncio default is fine.
        spawn_kwargs: dict[str, t.Any] = {}
        if sys.platform != "win32":
            spawn_kwargs["start_new_session"] = True

        self._process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd),
            env=merged_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **spawn_kwargs,
        )

        # Pipe drainers — capture-and-log line by line so callers get
        # immediate visibility into the tool's progress.
        assert self._process.stdout is not None
        assert self._process.stderr is not None
        self._drainers = [
            asyncio.create_task(
                self._drain(self._process.stdout, level=logging.INFO),
                name=f"{self._label}-stdout-drainer",
            ),
            asyncio.create_task(
                self._drain(
                    self._process.stderr,
                    level=logging.WARNING,
                    capture=self._stderr_buffer,
                ),
                name=f"{self._label}-stderr-drainer",
            ),
        ]

    async def wait(self) -> int:
        """Wait for the child to exit; return its exit code.

        Drains the stdout / stderr pipes to completion before returning.
        """
        if self._process is None:
            msg = "AsyncProcess.wait() called before start()"
            raise RuntimeError(msg)
        returncode = await self._process.wait()
        # Let the drainers consume any final buffered lines before
        # returning to the caller.
        await asyncio.gather(*self._drainers, return_exceptions=True)
        return returncode

    async def terminate(self, *, timeout: float = 5.0) -> int | None:
        """Send SIGTERM; escalate to SIGKILL after ``timeout`` seconds.

        Idempotent — calling on an already-exited process is a no-op
        and returns the existing exit code (or ``None`` if never started).

        Parameters
        ----------
        timeout
            Seconds to wait for graceful exit after SIGTERM.

        Returns
        -------
        int | None
            The child's exit code, or ``None`` if :meth:`start` was
            never called.
        """
        if self._process is None:
            return None
        if self._process.returncode is not None:
            return self._process.returncode

        self._process.terminate()
        try:
            await asyncio.wait_for(self._process.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            self._logger.warning(
                "[%s] did not exit within %.1fs of SIGTERM; sending SIGKILL",
                self._label,
                timeout,
            )
            # ProcessLookupError race: the child can exit between
            # TimeoutError and kill().
            with contextlib.suppress(ProcessLookupError):
                self._process.kill()
            await self._process.wait()

        # Wait for drainers to consume their last buffered line before
        # the caller proceeds; surface no exception if a drainer raised.
        await asyncio.gather(*self._drainers, return_exceptions=True)
        return self._process.returncode

    async def _drain(
        self,
        stream: asyncio.StreamReader,
        *,
        level: int,
        capture: list[str] | None = None,
    ) -> None:
        """Consume ``stream`` line by line; log each line.

        Optionally append every (non-empty) line to ``capture`` so callers
        can surface it in error messages.
        """
        while True:
            try:
                line = await stream.readline()
            except (BrokenPipeError, ConnectionResetError):
                return
            if not line:
                return
            text = line.decode("utf-8", errors="replace").rstrip("\n")
            if text:
                self._logger.log(level, "[%s] %s", self._label, text)
                if capture is not None:
                    capture.append(text)
