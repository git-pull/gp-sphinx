"""Sphinx event handlers that drive the Vite watch lifecycle.

The handlers live here (not in ``__init__.py``) so they're easy to unit
test in isolation: tests mock a Sphinx-like app, call the handler
directly, and assert against the process / bus instances stashed on
``app._gp_sphinx_vite_*``.

Lifecycle:

- ``builder-inited`` (:func:`on_builder_inited`) — resolve config; if
  ``should_spawn``, start the bus, spawn the watch process,  and stash
  both on ``app``. Idempotent: re-firing (sphinx-autobuild fires this
  on every rebuild) finds the running process and returns.
- ``build-finished`` (:func:`on_build_finished`) — no-op by default.
  The watch process keeps running across rebuilds so Vite can incrementally
  recompile on file changes. Teardown happens via :data:`atexit` and
  signal handlers installed at first spawn.

Tear-down is the responsibility of :func:`teardown`, which is wired
to ``atexit`` and to ``SIGINT`` / ``SIGTERM`` / ``SIGHUP``.

The handlers are passive about command construction: they call
:func:`gp_sphinx_vite.process.vite_watch_command` for the default Vite
argv. Tests monkey-patch that symbol when they want a fake-vite invocation.
"""

from __future__ import annotations

import atexit
import pathlib
import signal
import typing as t
import weakref

from sphinx.util import logging as sphinx_logging

from .bus import AsyncioBus
from .config import GpSphinxViteConfig, detect_mode, resolve_vite_root
from .process import ViteProcess, pnpm_install_command, vite_watch_command

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

# `sphinx.util.logging.getLogger` returns a SphinxLoggerAdapter that
# routes through Sphinx's status / warning streams — which means our
# `[vite] …` lines actually surface in `sphinx-autobuild` output the
# same way Sphinx's own messages do. The stdlib `logging.getLogger`
# does not propagate by default in Sphinx contexts.
logger = sphinx_logging.getLogger(__name__)

_BUS_ATTR = "_gp_sphinx_vite_bus"
_PROC_ATTR = "_gp_sphinx_vite_proc"
_TEARDOWN_REGISTERED_ATTR = "_gp_sphinx_vite_teardown_registered"

# Live (bus, proc) pairs that the global teardown handler should clean
# up. Held weakly so a Sphinx app being garbage-collected doesn't keep
# the bus thread alive.
_active_handles: weakref.WeakValueDictionary[int, AsyncioBus] = (
    weakref.WeakValueDictionary()
)


def _build_config(app: Sphinx) -> GpSphinxViteConfig:
    """Snapshot the live config values into a frozen dataclass."""
    return GpSphinxViteConfig(
        mode=detect_mode(config_value=app.config.gp_sphinx_vite_mode),
        vite_root=resolve_vite_root(app.config.gp_sphinx_vite_root),
    )


def _ensure_node_modules(vite_root: pathlib.Path, bus: AsyncioBus) -> bool:
    """Ensure ``<vite_root>/node_modules/`` exists; install if missing.

    Closes the developer-workflow gap where ``git clean -fdx`` wipes
    ``node_modules/`` and the next ``sphinx-autobuild`` would otherwise
    spawn ``pnpm exec vite`` against a missing tree, exit immediately
    with ``Command "vite" not found``, and silently leave the docs site
    serving 404s for ``furo-tw.css`` + ``furo.js``.

    Returns ``True`` if ``node_modules/`` exists (or was installed
    successfully); ``False`` if the install ran but exited non-zero,
    which signals to :func:`on_builder_inited` to skip the vite-watch
    spawn rather than burn cycles on a guaranteed-failed
    ``pnpm exec vite``.
    """
    if (vite_root / "node_modules").exists():
        return True

    install_cmd = pnpm_install_command()
    logger.info(
        "[vite] node_modules/ missing in %s; running `%s`",
        vite_root,
        " ".join(install_cmd),
    )
    install_proc = ViteProcess(label="pnpm-install", logger=logger)
    bus.call_sync(install_proc.start(install_cmd, cwd=vite_root))
    returncode = bus.call_sync(install_proc.wait())
    if returncode != 0:
        logger.warning(
            "[vite] pnpm install failed (exit %d) in %s — skipping vite "
            "spawn; run the install manually and restart sphinx-autobuild",
            returncode,
            vite_root,
        )
        return False
    logger.info("[vite] pnpm install complete; proceeding to vite-watch spawn")
    return True


def on_builder_inited(app: Sphinx) -> None:
    """``builder-inited`` event handler.

    Spawns the Vite watch process when the resolved config asks for it.
    Idempotent across multiple builder-inited firings (sphinx-autobuild
    re-fires this on every rebuild).

    If ``<vite_root>/node_modules/`` is missing (typical after
    ``git clean -fdx``), runs ``pnpm install --frozen-lockfile``
    synchronously first so ``pnpm exec vite`` resolves on first try.
    """
    config = _build_config(app)
    if not config.should_spawn:
        return

    existing_proc: ViteProcess | None = getattr(app, _PROC_ATTR, None)
    if existing_proc is not None and existing_proc.is_running:
        # sphinx-autobuild's repeated builder-inited; the watch is
        # already running, leave it alone.
        return

    bus = getattr(app, _BUS_ATTR, None)
    if bus is None:
        bus = AsyncioBus()
        bus.start()
        setattr(app, _BUS_ATTR, bus)
        _active_handles[id(app)] = bus

    if config.vite_root is None:
        # `should_spawn` already guards this, but tighten for type checkers.
        msg = "should_spawn was True but vite_root resolved to None"
        raise RuntimeError(msg)

    if not _ensure_node_modules(config.vite_root, bus):
        # Install failed; warning was already logged. Don't try to
        # spawn vite — pnpm exec would fail the same way.
        return

    proc = ViteProcess(label="vite", logger=logger)
    setattr(app, _PROC_ATTR, proc)

    command = vite_watch_command()
    logger.info("[vite] spawning %s in %s", " ".join(command), config.vite_root)
    bus.call_sync(proc.start(command, cwd=config.vite_root))

    if not getattr(app, _TEARDOWN_REGISTERED_ATTR, False):
        _install_teardown_handlers(app)
        setattr(app, _TEARDOWN_REGISTERED_ATTR, True)


def on_build_finished(app: Sphinx, exception: BaseException | None) -> None:
    """``build-finished`` event handler.

    Deliberately a no-op: keeping the watch alive across rebuilds is
    the whole point of the orchestration. Teardown happens via signal
    handlers and the :mod:`atexit` registration installed at first
    spawn.

    Logs the exception (if any) for context, but does not interfere
    with Sphinx's own error reporting.
    """
    if exception is not None:
        logger.debug(
            "[vite] sphinx build finished with exception (%s); leaving watch alive",
            exception,
        )


def teardown(app: Sphinx, *, terminate_timeout: float = 5.0) -> None:
    """Stop the Vite watch and tear down the bus for ``app``.

    Idempotent: safe to call from multiple signal sources (atexit +
    SIGINT) without double-stop errors.
    """
    proc: ViteProcess | None = getattr(app, _PROC_ATTR, None)
    bus: AsyncioBus | None = getattr(app, _BUS_ATTR, None)
    if proc is None and bus is None:
        return

    if proc is not None and bus is not None:
        try:
            bus.call_sync(proc.terminate(timeout=terminate_timeout))
        except Exception as exc:
            logger.warning("[vite] terminate raised during teardown: %s", exc)

    if bus is not None:
        bus.stop(timeout=terminate_timeout)

    setattr(app, _PROC_ATTR, None)
    setattr(app, _BUS_ATTR, None)


def _install_teardown_handlers(app: Sphinx) -> None:
    """Wire :data:`atexit` + signal handlers to tear down ``app``'s watch.

    Uses a weak reference to the app so a long-lived Python process
    holding the handler doesn't keep the app alive past its natural
    lifetime.
    """
    app_ref = weakref.ref(app)

    def _handle_atexit() -> None:
        live_app = app_ref()
        if live_app is not None:
            teardown(live_app)

    atexit.register(_handle_atexit)

    previous_handlers: dict[int, t.Any] = {}
    for sig_name in ("SIGINT", "SIGTERM", "SIGHUP"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue  # Windows lacks SIGHUP, etc.

        def _make_handler(
            sig: int,
            previous: t.Any = None,
        ) -> t.Callable[[int, t.Any], None]:
            def _handle(signum: int, frame: t.Any) -> None:
                live_app = app_ref()
                if live_app is not None:
                    teardown(live_app)
                if callable(previous):
                    previous(signum, frame)
                # Re-raise the signal once cleanup is done so the
                # default behavior (process exit) follows.
                if previous in (signal.SIG_DFL, None):
                    signal.signal(signum, signal.SIG_DFL)
                    signal.raise_signal(signum)

            return _handle

        previous = signal.getsignal(sig)
        previous_handlers[sig] = previous
        signal.signal(sig, _make_handler(sig, previous))
