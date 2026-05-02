"""Tests for :class:`gp_sphinx_vite.process.ViteProcess`.

Drives the design via TDD against a synthetic "fake-vite" Python
script generated per-test. The fake script is parametric — accepts
flags for output-rate, exit-on, and SIGTERM-ignoring — so each
spawn / log / terminate / kill scenario gets its own focused
fixture without shelling out to a system tool.
"""

from __future__ import annotations

import asyncio
import logging
import pathlib
import sys
import textwrap
import typing as t

import pytest
from gp_sphinx_vite.process import ViteProcess, vite_watch_command


def _write_fake_vite(
    tmp_path: pathlib.Path,
    *,
    body: str,
) -> pathlib.Path:
    """Write ``body`` to a fake-vite script and return its path.

    Each test gets its own script so we can vary behavior cheaply.
    """
    path = tmp_path / "fake_vite.py"
    path.write_text(textwrap.dedent(body))
    return path


def _fake_vite_argv(script: pathlib.Path) -> list[str]:
    return [sys.executable, str(script)]


@pytest.mark.asyncio
async def test_start_runs_quick_command_and_exits(tmp_path: pathlib.Path) -> None:
    """A short script that prints once and exits 0 returns 0."""
    script = _write_fake_vite(
        tmp_path,
        body="""\
        import sys
        print("vite v7 ready")
        sys.exit(0)
        """,
    )
    proc = ViteProcess(label="fake")
    await proc.start(_fake_vite_argv(script), cwd=tmp_path)
    code = await proc.wait()
    assert code == 0
    assert not proc.is_running


@pytest.mark.asyncio
async def test_stdout_lines_logged_with_label_prefix(
    tmp_path: pathlib.Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Each stdout line lands in the log with the configured ``[label]`` prefix."""
    script = _write_fake_vite(
        tmp_path,
        body="""\
        import sys
        print("built furo.css in 12ms")
        print("watching for changes")
        sys.exit(0)
        """,
    )
    custom_logger = logging.getLogger("test_gp_sphinx_vite.fake")
    proc = ViteProcess(label="fake", logger=custom_logger)
    with caplog.at_level(logging.INFO, logger=custom_logger.name):
        await proc.start(_fake_vite_argv(script), cwd=tmp_path)
        await proc.wait()
    messages = [r.getMessage() for r in caplog.records if r.name == custom_logger.name]
    assert "[fake] built furo.css in 12ms" in messages
    assert "[fake] watching for changes" in messages


@pytest.mark.asyncio
async def test_stderr_lines_logged_at_warning_level(
    tmp_path: pathlib.Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Each stderr line surfaces at WARNING (so Sphinx's `app.warn` aligns)."""
    script = _write_fake_vite(
        tmp_path,
        body="""\
        import sys
        print("vite warning: deprecated rule", file=sys.stderr)
        sys.exit(0)
        """,
    )
    custom_logger = logging.getLogger("test_gp_sphinx_vite.fake_stderr")
    proc = ViteProcess(label="fake", logger=custom_logger)
    with caplog.at_level(logging.WARNING, logger=custom_logger.name):
        await proc.start(_fake_vite_argv(script), cwd=tmp_path)
        await proc.wait()
    warnings = [
        r
        for r in caplog.records
        if r.name == custom_logger.name and r.levelno == logging.WARNING
    ]
    assert any(
        r.getMessage() == "[fake] vite warning: deprecated rule" for r in warnings
    )


@pytest.mark.asyncio
async def test_terminate_signals_long_running_process(tmp_path: pathlib.Path) -> None:
    """A long-running script terminates promptly under SIGTERM."""
    script = _write_fake_vite(
        tmp_path,
        body="""\
        import time
        while True:
            time.sleep(0.5)
        """,
    )
    proc = ViteProcess(label="fake")
    await proc.start(_fake_vite_argv(script), cwd=tmp_path)
    assert proc.is_running
    await asyncio.sleep(0.05)  # let the child get into its sleep
    code = await proc.terminate(timeout=2.0)
    assert not proc.is_running
    # SIGTERM exits with -SIGTERM (-15) on POSIX; some platforms vary.
    assert code is not None
    assert code != 0


@pytest.mark.asyncio
async def test_terminate_escalates_to_sigkill_when_sigterm_ignored(
    tmp_path: pathlib.Path,
) -> None:
    """A script that traps SIGTERM is force-killed after the timeout."""
    script = _write_fake_vite(
        tmp_path,
        body="""\
        import signal, time
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        while True:
            time.sleep(0.5)
        """,
    )
    proc = ViteProcess(label="fake")
    await proc.start(_fake_vite_argv(script), cwd=tmp_path)
    await asyncio.sleep(0.05)
    code = await proc.terminate(timeout=0.5)
    assert not proc.is_running
    assert code is not None  # SIGKILL exit -9 — escaped from SIG_IGN trap


@pytest.mark.asyncio
async def test_terminate_idempotent_on_exited_process(tmp_path: pathlib.Path) -> None:
    """Calling terminate after natural exit is a no-op (doesn't raise)."""
    script = _write_fake_vite(
        tmp_path,
        body="""\
        import sys
        print("done")
        sys.exit(7)
        """,
    )
    proc = ViteProcess(label="fake")
    await proc.start(_fake_vite_argv(script), cwd=tmp_path)
    await proc.wait()
    assert proc.returncode == 7
    # Second-call terminate must not blow up.
    code = await proc.terminate(timeout=1.0)
    assert code == 7


@pytest.mark.asyncio
async def test_terminate_no_op_before_start() -> None:
    """terminate() on an unstarted process returns None silently."""
    proc = ViteProcess()
    assert await proc.terminate() is None
    assert not proc.is_running


@pytest.mark.asyncio
async def test_double_start_raises(tmp_path: pathlib.Path) -> None:
    """start() twice on the same instance is a programming error."""
    script = _write_fake_vite(tmp_path, body="import sys; sys.exit(0)\n")
    proc = ViteProcess()
    await proc.start(_fake_vite_argv(script), cwd=tmp_path)
    with pytest.raises(RuntimeError, match=r"start.*twice"):
        await proc.start(_fake_vite_argv(script), cwd=tmp_path)
    await proc.wait()


@pytest.mark.asyncio
async def test_wait_before_start_raises() -> None:
    """wait() on an unstarted process is a programming error."""
    proc = ViteProcess()
    with pytest.raises(RuntimeError, match=r"wait.*before start"):
        await proc.wait()


@pytest.mark.asyncio
async def test_pythonunbuffered_injected_into_child_env(tmp_path: pathlib.Path) -> None:
    """``PYTHONUNBUFFERED=1`` is set in the child env even if absent from caller env."""
    script = _write_fake_vite(
        tmp_path,
        body="""\
        import os, sys
        sys.exit(0 if os.environ.get("PYTHONUNBUFFERED") == "1" else 1)
        """,
    )
    proc = ViteProcess(label="fake")
    # Caller's env does NOT have the var; expect it to be injected.
    sentinel_env: dict[str, str] = {"PATH": __import__("os").environ.get("PATH", "")}
    await proc.start(_fake_vite_argv(script), cwd=tmp_path, env=sentinel_env)
    code = await proc.wait()
    assert code == 0


def test_vite_watch_command_default() -> None:
    """The canonical watch argv is the pnpm exec form."""
    assert vite_watch_command() == ("pnpm", "exec", "vite", "build", "--watch")


def test_vite_watch_command_alternate_package_manager() -> None:
    """The package_manager kwarg overrides the runner."""
    assert vite_watch_command(package_manager="npm") == (
        "npm",
        "exec",
        "vite",
        "build",
        "--watch",
    )


def test_vite_watch_command_returns_tuple_for_pass_through() -> None:
    """Output is a tuple (immutable; safe to pass into subprocess primitives)."""
    cmd: t.Tuple[str, ...] = vite_watch_command()  # noqa: UP006 — narrow assertion
    assert isinstance(cmd, tuple)
