"""Async subprocess wrapper for the Vite watch command.

Wraps :func:`asyncio.create_subprocess_exec` with the conventions the
orchestration layer needs:

- ``stdout``/``stderr`` are piped through line-buffered drainers that
  prefix each line with a label (``[vite]`` by default) and route them
  to a :class:`logging.Logger` — info for stdout, warning for stderr.
  Mirrors the pattern in ``/home/d/scripts/py/image360/dev_server.py``.
- ``PYTHONUNBUFFERED=1`` is forced into the child env so Python tools
  invoked via the package-manager bridge don't withhold their output.
- :meth:`ViteProcess.terminate` is graceful-then-forceful: SIGTERM,
  await up to ``timeout`` seconds, escalate to SIGKILL if the child is
  still alive. Idempotent: calling on an already-exited process is a
  no-op.

Argument lists are passed directly to ``create_subprocess_exec``; no
shell, no string interpolation, no command injection surface.

The class is generic over "what command to run" so the same wrapper
covers the production watch command and the fake-Vite shell scripts
used in tests.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import pathlib
import typing as t

if t.TYPE_CHECKING:
    pass

_module_logger = logging.getLogger(__name__)


class ViteProcess:
    """Async wrapper around a long-running Vite child process."""

    def __init__(
        self,
        *,
        label: str = "vite",
        logger: logging.Logger | None = None,
    ) -> None:
        self._label = label
        self._logger = logger if logger is not None else _module_logger
        self._process: asyncio.subprocess.Process | None = None
        self._drainers: list[asyncio.Task[None]] = []

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

    async def start(
        self,
        command: t.Sequence[str],
        *,
        cwd: pathlib.Path,
        env: t.Mapping[str, str] | None = None,
    ) -> None:
        """Spawn ``command`` and start draining its stdout/stderr.

        Parameters
        ----------
        command
            Argument list. Passed straight to the asyncio subprocess
            primitive; no shell.
        cwd
            Working directory for the child. Must contain ``package.json``
            for a real package-manager invocation.
        env
            Optional environment override. ``PYTHONUNBUFFERED=1`` is always
            injected on top of whatever this provides (or, if ``None``,
            on top of :data:`os.environ`).

        Raises
        ------
        RuntimeError
            If :meth:`start` is called twice on the same instance without
            an intervening :meth:`terminate`.
        """
        if self._process is not None:
            msg = "ViteProcess.start() called twice; spawn a new instance instead"
            raise RuntimeError(msg)

        merged_env = dict(env) if env is not None else dict(os.environ)
        merged_env["PYTHONUNBUFFERED"] = "1"

        self._process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd),
            env=merged_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Pipe drainers — capture-and-log line by line so the parent
        # process gets immediate visibility into Vite's progress.
        assert self._process.stdout is not None
        assert self._process.stderr is not None
        self._drainers = [
            asyncio.create_task(
                self._drain(self._process.stdout, level=logging.INFO),
                name=f"{self._label}-stdout-drainer",
            ),
            asyncio.create_task(
                self._drain(self._process.stderr, level=logging.WARNING),
                name=f"{self._label}-stderr-drainer",
            ),
        ]

    async def wait(self) -> int:
        """Wait for the child to exit; return its exit code.

        Drains the stdout/stderr pipes to completion before returning.
        """
        if self._process is None:
            msg = "ViteProcess.wait() called before start()"
            raise RuntimeError(msg)
        returncode = await self._process.wait()
        # Let the drainers consume any final buffered lines before returning.
        await asyncio.gather(*self._drainers, return_exceptions=True)
        return returncode

    async def terminate(self, *, timeout: float = 5.0) -> int | None:
        """Send SIGTERM; escalate to SIGKILL after ``timeout`` seconds.

        Idempotent — calling on an already-exited process is a no-op
        and returns the existing exit code (or ``None`` if never started).

        Parameters
        ----------
        timeout
            Seconds to wait for graceful exit after SIGTERM. ``5.0`` is
            the same default the plan calls for; matches the cleanup
            pattern in ``/home/d/scripts/py/image360/dev_server.py``.

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
            # ProcessLookupError race: child can exit between
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
    ) -> None:
        """Consume ``stream`` line by line; log each line through ``self._logger``."""
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


def vite_watch_command(*, package_manager: str = "pnpm") -> tuple[str, ...]:
    """Build the canonical Vite-watch argv.

    The output is a tuple suitable for passing straight into
    :meth:`ViteProcess.start`. No shell metacharacters, no
    interpolation: each token is a separate argv entry.

    Examples
    --------
    >>> vite_watch_command()
    ('pnpm', 'exec', 'vite', 'build', '--watch')
    >>> vite_watch_command(package_manager="npm")
    ('npm', 'exec', 'vite', 'build', '--watch')
    """
    return (package_manager, "exec", "vite", "build", "--watch")
