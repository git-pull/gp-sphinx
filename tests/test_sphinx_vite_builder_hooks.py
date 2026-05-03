"""Tests for :mod:`sphinx_vite_builder._internal.hooks`.

The hooks layer wires an :class:`AsyncProcess` to Sphinx's lifecycle
events. Tests use a thin Sphinx-app stand-in (with ``.config`` and the
four attributes the hooks set) and a fake-vite Python script in
``tmp_path`` so each test can exercise the real subprocess +
``AsyncioBus`` + ``AsyncProcess`` chain end-to-end without booting a
full Sphinx build.
"""

from __future__ import annotations

import dataclasses
import pathlib
import sys
import textwrap
import time

import pytest
from sphinx_vite_builder._internal import hooks


@dataclasses.dataclass
class _FakeConfig:
    """The slice of ``app.config`` the hooks read."""

    sphinx_vite_builder_mode: str = "auto"
    sphinx_vite_builder_root: str | None = None


@dataclasses.dataclass
class _FakeApp:
    """Minimal stand-in for ``sphinx.application.Sphinx``.

    Carries only the surface the hooks touch: a ``config`` namespace
    and the few private attributes the hooks ``setattr`` onto the app
    (bus, proc, teardown-registered flag).
    """

    config: _FakeConfig = dataclasses.field(default_factory=_FakeConfig)


def _write_fake_vite(
    tmp_path: pathlib.Path, *, body: str, with_node_modules: bool = True
) -> pathlib.Path:
    """Write a fake-vite script + a stub package.json at ``tmp_path``.

    Creates ``node_modules/`` by default so :func:`hooks._ensure_node_modules`
    short-circuits the auto-install path. Tests that exercise the install
    path explicitly pass ``with_node_modules=False`` and arrange their own
    ``pnpm_install_command`` patch.
    """
    (tmp_path / "package.json").write_text('{"name": "fake-vite-root"}\n')
    if with_node_modules:
        (tmp_path / "node_modules").mkdir(exist_ok=True)
    script = tmp_path / "fake_vite.py"
    script.write_text(textwrap.dedent(body))
    return script


def _patch_vite_command(monkeypatch: pytest.MonkeyPatch, script: pathlib.Path) -> None:
    """Replace ``vite_watch_command()`` with one that runs ``script``."""

    def _fake_command() -> tuple[str, ...]:
        return (sys.executable, str(script))

    # Patch where hooks reads the symbol from (its own module namespace).
    monkeypatch.setattr(hooks, "vite_watch_command", _fake_command)


def _patch_install_command(
    monkeypatch: pytest.MonkeyPatch, script: pathlib.Path
) -> None:
    """Replace ``pnpm_install_command()`` with one that runs ``script``."""

    def _fake_command() -> tuple[str, ...]:
        return (sys.executable, str(script))

    monkeypatch.setattr(hooks, "pnpm_install_command", _fake_command)


@pytest.fixture
def long_running_fake_vite(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> _FakeApp:
    """Fake-vite that loops forever; a teardown is required to clean up."""
    script = _write_fake_vite(
        tmp_path,
        body="""\
        import sys, time
        # Print one ready-line so a human running this can see progress.
        print("vite watching", flush=True)
        while True:
            time.sleep(0.1)
        """,
    )
    _patch_vite_command(monkeypatch, script)
    return _FakeApp(
        config=_FakeConfig(
            sphinx_vite_builder_mode="dev",
            sphinx_vite_builder_root=str(tmp_path),
        ),
    )


def test_on_builder_inited_no_op_in_prod_mode(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`mode="prod"` → no process spawned, no bus started."""
    app = _FakeApp(
        config=_FakeConfig(
            sphinx_vite_builder_mode="prod",
            sphinx_vite_builder_root=str(tmp_path),
        ),
    )

    def _fail() -> tuple[str, ...]:
        msg = "vite_watch_command should not be called in prod mode"
        raise AssertionError(msg)

    monkeypatch.setattr(hooks, "vite_watch_command", _fail)
    hooks.on_builder_inited(app)  # type: ignore[arg-type]
    assert getattr(app, hooks._PROC_ATTR, None) is None
    assert getattr(app, hooks._BUS_ATTR, None) is None


def test_on_builder_inited_runs_one_shot_in_prod_mode(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`mode="prod"` with a vite_root → one-shot run_vite_build, no spawn.

    Covers the PROD branch added alongside the placeholder rewrite: under
    plain ``sphinx-build`` the extension delegates to the same orchestration
    primitive the PEP 517 backend uses, blocking the build until vite
    finishes and never spawning the long-running watch.
    """
    captured: list[pathlib.Path | None] = []

    def _capture(
        project_root: pathlib.Path | None = None,
        *,
        package_manager: str = "pnpm",
    ) -> None:
        del package_manager
        captured.append(project_root)

    monkeypatch.setattr(hooks, "run_vite_build", _capture)

    vite_root = tmp_path / "web"
    vite_root.mkdir()
    app = _FakeApp(
        config=_FakeConfig(
            sphinx_vite_builder_mode="prod",
            sphinx_vite_builder_root=str(vite_root),
        ),
    )

    hooks.on_builder_inited(app)  # type: ignore[arg-type]

    # `run_vite_build` resolves `web/` relative to its `project_root`
    # arg, so the hook passes the parent of vite_root.
    assert captured == [vite_root.parent.resolve()]
    # PROD path is one-shot: no watch process, no bus.
    assert getattr(app, hooks._PROC_ATTR, None) is None
    assert getattr(app, hooks._BUS_ATTR, None) is None


def test_on_builder_inited_no_op_when_root_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`mode="dev"` but no root → still no spawn (config.should_spawn is False)."""
    app = _FakeApp(
        config=_FakeConfig(
            sphinx_vite_builder_mode="dev",
            sphinx_vite_builder_root=None,
        ),
    )

    def _fail() -> tuple[str, ...]:
        msg = "vite_watch_command should not be called when root is None"
        raise AssertionError(msg)

    monkeypatch.setattr(hooks, "vite_watch_command", _fail)
    hooks.on_builder_inited(app)  # type: ignore[arg-type]
    assert getattr(app, hooks._PROC_ATTR, None) is None


def test_on_builder_inited_spawns_when_should_spawn(
    long_running_fake_vite: _FakeApp,
) -> None:
    """A dev-mode app with a real root spawns the watch."""
    app = long_running_fake_vite
    try:
        hooks.on_builder_inited(app)  # type: ignore[arg-type]
        proc = getattr(app, hooks._PROC_ATTR, None)
        bus = getattr(app, hooks._BUS_ATTR, None)
        assert proc is not None
        assert bus is not None
        assert bus.is_running
        # Give the child a moment to actually spawn before asserting.
        deadline = time.monotonic() + 1.0
        while not proc.is_running and time.monotonic() < deadline:
            time.sleep(0.01)
        assert proc.is_running
    finally:
        hooks.teardown(app, terminate_timeout=2.0)  # type: ignore[arg-type]


def test_on_builder_inited_is_idempotent_on_refire(
    long_running_fake_vite: _FakeApp,
) -> None:
    """sphinx-autobuild's repeated builder-inited doesn't double-spawn."""
    app = long_running_fake_vite
    try:
        hooks.on_builder_inited(app)  # type: ignore[arg-type]
        first_proc = getattr(app, hooks._PROC_ATTR, None)
        first_pid = first_proc.pid if first_proc else None

        # Re-fire: simulating sphinx-autobuild's behavior.
        hooks.on_builder_inited(app)  # type: ignore[arg-type]
        second_proc = getattr(app, hooks._PROC_ATTR, None)
        second_pid = second_proc.pid if second_proc else None

        assert first_proc is second_proc
        assert first_pid == second_pid
    finally:
        hooks.teardown(app, terminate_timeout=2.0)  # type: ignore[arg-type]


def test_on_build_finished_leaves_watch_running(
    long_running_fake_vite: _FakeApp,
) -> None:
    """build-finished is a no-op: the watch keeps running for the next rebuild."""
    app = long_running_fake_vite
    try:
        hooks.on_builder_inited(app)  # type: ignore[arg-type]
        proc = getattr(app, hooks._PROC_ATTR, None)
        assert proc is not None
        deadline = time.monotonic() + 1.0
        while not proc.is_running and time.monotonic() < deadline:
            time.sleep(0.01)
        assert proc.is_running

        hooks.on_build_finished(app, exception=None)  # type: ignore[arg-type]
        # Still running after build-finished.
        assert proc.is_running
    finally:
        hooks.teardown(app, terminate_timeout=2.0)  # type: ignore[arg-type]


def test_teardown_terminates_process_and_stops_bus(
    long_running_fake_vite: _FakeApp,
) -> None:
    """Explicit teardown stops both the process and the bus, idempotently."""
    app = long_running_fake_vite
    hooks.on_builder_inited(app)  # type: ignore[arg-type]
    proc = getattr(app, hooks._PROC_ATTR, None)
    bus = getattr(app, hooks._BUS_ATTR, None)
    assert proc is not None and bus is not None

    hooks.teardown(app, terminate_timeout=2.0)  # type: ignore[arg-type]

    assert not proc.is_running
    assert not bus.is_running
    assert getattr(app, hooks._PROC_ATTR, None) is None
    assert getattr(app, hooks._BUS_ATTR, None) is None

    # Calling teardown again is a no-op.
    hooks.teardown(app, terminate_timeout=2.0)  # type: ignore[arg-type]


def test_teardown_no_op_when_never_spawned() -> None:
    """Teardown on an app that never reached should_spawn does nothing harmful."""
    app = _FakeApp()
    hooks.teardown(app)  # type: ignore[arg-type]


def test_on_build_finished_logs_exception(
    long_running_fake_vite: _FakeApp,
) -> None:
    """An exception passed to build-finished surfaces at DEBUG (not WARNING).

    Sphinx's logger setup (memory handlers, namespace prefix) interacts
    with pytest's ``caplog`` in test-order-dependent ways once any
    Sphinx scenario fixture has initialized a real Sphinx app. Sidestep
    by attaching our own handler directly to the underlying stdlib
    Logger that ``sphinx.util.logging.getLogger`` wraps.
    """
    import logging

    app = long_running_fake_vite
    captured: list[logging.LogRecord] = []

    class _CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    handler = _CaptureHandler(level=logging.DEBUG)
    underlying = logging.getLogger("sphinx.sphinx_vite_builder._internal.hooks")
    underlying.addHandler(handler)
    underlying.setLevel(logging.DEBUG)

    try:
        hooks.on_builder_inited(app)  # type: ignore[arg-type]
        hooks.on_build_finished(
            app,  # type: ignore[arg-type]
            exception=RuntimeError("sphinx fell over"),
        )
        assert any("sphinx fell over" in r.getMessage() for r in captured), [
            r.getMessage() for r in captured
        ]
    finally:
        underlying.removeHandler(handler)
        hooks.teardown(app, terminate_timeout=2.0)  # type: ignore[arg-type]


def test_on_builder_inited_skips_install_when_node_modules_present(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pre-existing node_modules/ → no install attempt; vite spawns directly."""
    # Pre-create node_modules so _ensure_node_modules sees it as present.
    (tmp_path / "node_modules").mkdir()
    vite_script = _write_fake_vite(
        tmp_path,
        body="""\
        import time
        print("vite watching", flush=True)
        while True:
            time.sleep(0.1)
        """,
    )
    _patch_vite_command(monkeypatch, vite_script)

    def _fail_install() -> tuple[str, ...]:
        msg = "pnpm_install_command should not be called when node_modules/ exists"
        raise AssertionError(msg)

    monkeypatch.setattr(hooks, "pnpm_install_command", _fail_install)

    app = _FakeApp(
        config=_FakeConfig(
            sphinx_vite_builder_mode="dev",
            sphinx_vite_builder_root=str(tmp_path),
        ),
    )
    try:
        hooks.on_builder_inited(app)  # type: ignore[arg-type]
        proc = getattr(app, hooks._PROC_ATTR, None)
        assert proc is not None, "vite should have spawned"
    finally:
        hooks.teardown(app, terminate_timeout=2.0)  # type: ignore[arg-type]


def test_on_builder_inited_runs_install_when_node_modules_missing(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing node_modules/ → install runs (and creates it), then vite spawns.

    The install marker file (``installed.flag``) is the deterministic proof
    the fake-pnpm script ran; ``node_modules/`` creation is the side-effect
    that silences subsequent _ensure_node_modules calls on a re-fire.
    """
    install_marker = tmp_path / "installed.flag"
    install_script = tmp_path / "fake_pnpm.py"
    install_script.write_text(
        textwrap.dedent(
            f"""\
            import pathlib
            (pathlib.Path({str(install_marker)!r})).write_text("ran")
            (pathlib.Path({str(tmp_path / "node_modules")!r})).mkdir()
            """,
        ),
    )
    vite_script = _write_fake_vite(
        tmp_path,
        with_node_modules=False,
        body="""\
        import time
        print("vite watching", flush=True)
        while True:
            time.sleep(0.1)
        """,
    )
    _patch_vite_command(monkeypatch, vite_script)
    _patch_install_command(monkeypatch, install_script)

    app = _FakeApp(
        config=_FakeConfig(
            sphinx_vite_builder_mode="dev",
            sphinx_vite_builder_root=str(tmp_path),
        ),
    )
    try:
        hooks.on_builder_inited(app)  # type: ignore[arg-type]
        assert install_marker.exists(), "fake-pnpm install should have run"
        assert (tmp_path / "node_modules").exists(), (
            "install should have created node_modules"
        )
        proc = getattr(app, hooks._PROC_ATTR, None)
        assert proc is not None, "vite should have spawned after successful install"
    finally:
        hooks.teardown(app, terminate_timeout=2.0)  # type: ignore[arg-type]


def test_on_builder_inited_skips_vite_when_install_fails(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Install exits non-zero → vite is not spawned; warning is logged."""
    install_script = tmp_path / "fake_pnpm.py"
    install_script.write_text(
        textwrap.dedent(
            """\
            import sys
            print("simulated pnpm-install failure", flush=True)
            sys.exit(1)
            """,
        ),
    )

    def _fail_vite() -> tuple[str, ...]:
        msg = "vite_watch_command should not be called after install failure"
        raise AssertionError(msg)

    monkeypatch.setattr(hooks, "vite_watch_command", _fail_vite)
    _patch_install_command(monkeypatch, install_script)

    # We still need a package.json so config.should_spawn passes the
    # vite_root resolution check.
    (tmp_path / "package.json").write_text('{"name": "fake-vite-root"}\n')

    app = _FakeApp(
        config=_FakeConfig(
            sphinx_vite_builder_mode="dev",
            sphinx_vite_builder_root=str(tmp_path),
        ),
    )
    hooks.on_builder_inited(app)  # type: ignore[arg-type]
    # No vite process should have been set on the app.
    assert getattr(app, hooks._PROC_ATTR, None) is None, (
        "vite must not be spawned after a failed install"
    )
    hooks.teardown(app, terminate_timeout=2.0)  # type: ignore[arg-type]


def test_private_attr_names_are_stable() -> None:
    """The private attribute names the hooks set on app are part of the contract."""
    assert hooks._BUS_ATTR == "_sphinx_vite_builder_bus"
    assert hooks._PROC_ATTR == "_sphinx_vite_builder_proc"


_PRIVATE_ATTRS_TYPED: tuple[str, str, str] = (
    hooks._BUS_ATTR,
    hooks._PROC_ATTR,
    hooks._TEARDOWN_REGISTERED_ATTR,
)


def test_all_private_attrs_share_prefix() -> None:
    """Every private attribute starts with `_sphinx_vite_builder_`."""
    for attr in _PRIVATE_ATTRS_TYPED:
        assert attr.startswith("_sphinx_vite_builder_"), attr
