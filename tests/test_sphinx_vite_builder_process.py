"""Tests for :class:`sphinx_vite_builder._internal.process.AsyncProcess`.

Focused on the POSIX process-group teardown contract: ``terminate``
MUST signal the whole process group (so ``pnpm exec``'s ``vite`` child
exits) rather than only the leader's PID. The latter is what
``asyncio.subprocess.Process.terminate`` would do, and it leaves the
vite child orphaned because pnpm's ``exec`` command does not forward
signals to its target.

The unit tests monkeypatch ``os.killpg`` so they are deterministic and
don't depend on real process trees; an end-to-end behavioural test
exercises the integrated terminate path with a fake child that traps
SIGTERM.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import signal
import sys
import textwrap

import pytest
from sphinx_vite_builder._internal.process import AsyncProcess


def _write_fake_child(
    tmp_path: pathlib.Path,
    *,
    body: str,
) -> pathlib.Path:
    """Write ``body`` to a synthetic Python script under ``tmp_path``."""
    path = tmp_path / "fake_child.py"
    path.write_text(textwrap.dedent(body))
    return path


def _fake_child_argv(script: pathlib.Path) -> list[str]:
    return [sys.executable, str(script)]


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="killpg is POSIX-only; Windows uses Process.terminate()",
)
@pytest.mark.asyncio
async def test_terminate_sends_sigterm_to_process_group_on_posix(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``terminate`` MUST call ``os.killpg(pid, SIGTERM)`` on POSIX."""
    script = _write_fake_child(
        tmp_path,
        body="""\
        import time
        while True:
            time.sleep(0.5)
        """,
    )
    proc = AsyncProcess(label="fake")
    await proc.start(_fake_child_argv(script), cwd=tmp_path)
    await asyncio.sleep(0.05)  # let the child reach its sleep loop
    pid = proc.pid
    assert pid is not None

    calls: list[tuple[int, int]] = []
    real_killpg = os.killpg

    def _spy_killpg(pgid: int, sig: int) -> None:
        calls.append((pgid, sig))
        real_killpg(pgid, sig)

    monkeypatch.setattr(os, "killpg", _spy_killpg)
    code = await proc.terminate(timeout=2.0)
    assert (pid, signal.SIGTERM) in calls
    assert not proc.is_running
    assert code is not None and code != 0


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="killpg is POSIX-only; Windows uses Process.kill()",
)
@pytest.mark.asyncio
async def test_terminate_escalates_to_killpg_sigkill_on_timeout(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A SIGTERM-trapping child is force-killed via ``killpg(pid, SIGKILL)``."""
    script = _write_fake_child(
        tmp_path,
        body="""\
        import signal, time
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        while True:
            time.sleep(0.5)
        """,
    )
    proc = AsyncProcess(label="fake")
    await proc.start(_fake_child_argv(script), cwd=tmp_path)
    await asyncio.sleep(0.05)
    pid = proc.pid
    assert pid is not None

    calls: list[tuple[int, int]] = []
    real_killpg = os.killpg

    def _spy_killpg(pgid: int, sig: int) -> None:
        calls.append((pgid, sig))
        real_killpg(pgid, sig)

    monkeypatch.setattr(os, "killpg", _spy_killpg)
    code = await proc.terminate(timeout=0.3)
    assert (pid, signal.SIGTERM) in calls
    assert (pid, signal.SIGKILL) in calls
    assert not proc.is_running
    assert code is not None  # escaped from SIG_IGN via SIGKILL


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="killpg is POSIX-only",
)
@pytest.mark.asyncio
async def test_terminate_swallows_processlookuperror(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A racing exit between checks and ``killpg`` MUST NOT raise.

    Reproduces the race: ``terminate`` sees ``returncode is None`` and
    proceeds to ``killpg``, but the child has already exited by the
    time the syscall fires. The child here exits naturally during the
    wait window so the ``Process.wait()`` call still resolves cleanly.
    """
    script = _write_fake_child(
        tmp_path,
        body="""\
        import sys, time
        time.sleep(0.2)
        sys.exit(0)
        """,
    )
    proc = AsyncProcess(label="fake")
    await proc.start(_fake_child_argv(script), cwd=tmp_path)
    await asyncio.sleep(0.05)  # child still alive at this point

    def _raise_lookup(pgid: int, sig: int) -> None:
        raise ProcessLookupError(pgid, sig)

    monkeypatch.setattr(os, "killpg", _raise_lookup)
    # ProcessLookupError from killpg MUST be swallowed; the child
    # then exits naturally and wait() returns its real exit code.
    code = await asyncio.wait_for(proc.terminate(timeout=2.0), timeout=5.0)
    assert code == 0
    assert not proc.is_running


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows fallback path uses Process.terminate()/kill()",
)
@pytest.mark.asyncio
async def test_terminate_uses_process_terminate_on_windows(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows has no ``killpg``; the fallback path signals the leader."""
    script = _write_fake_child(
        tmp_path,
        body="""\
        import time
        while True:
            time.sleep(0.5)
        """,
    )
    proc = AsyncProcess(label="fake")
    await proc.start(_fake_child_argv(script), cwd=tmp_path)
    await asyncio.sleep(0.05)

    terminate_calls = 0
    real_terminate = asyncio.subprocess.Process.terminate

    def _spy_terminate(self: asyncio.subprocess.Process) -> None:
        nonlocal terminate_calls
        terminate_calls += 1
        real_terminate(self)

    monkeypatch.setattr(
        asyncio.subprocess.Process,
        "terminate",
        _spy_terminate,
    )
    await proc.terminate(timeout=2.0)
    assert terminate_calls >= 1
    assert not proc.is_running
