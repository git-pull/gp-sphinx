"""Mode detection + config dataclass for the Sphinx-extension head.

Pure functions where possible — keeps the unit tests cheap (no Sphinx
fixture, no subprocess). The Sphinx-aware glue lives in :mod:`hooks`.

Mode detection inspects ``argv``, ``SPHINX_AUTOBUILD``, and the parent
process's command line so the orchestration becomes a no-op for
``sphinx-build`` invocations and turns on for ``sphinx-autobuild``.
"""

from __future__ import annotations

import dataclasses
import enum
import os
import pathlib
import sys
import typing as t


class Mode(str, enum.Enum):
    """Resolved orchestration mode.

    `str` mixin so the value compares equal to the literal string the
    user wrote in ``conf.py``.
    """

    DEV = "dev"
    PROD = "prod"


def _parent_is_sphinx_autobuild() -> bool:
    """Return True if our parent process's argv contains ``sphinx-autobuild``.

    Why this exists: ``sphinx-autobuild`` runs the actual Sphinx build
    in a *subprocess* via ``subprocess.run([sys.executable] + sphinx_args)``
    (see ``sphinx_autobuild/build.py:50``). In that subprocess,
    ``sys.argv[0]`` is the Python interpreter path, NOT
    ``sphinx-autobuild``, so the argv-based mode-detection misses it.
    Reading ``/proc/<ppid>/cmdline`` lets us see the parent's actual
    command line.

    Linux-only via ``/proc``. Returns ``False`` cleanly on macOS,
    Windows, or any other platform without ``/proc`` (and on Linux if
    the read fails for permission reasons). Test harnesses can disable
    this check by passing a stub via ``detect_mode(parent_check=...)``.
    """
    try:
        ppid = os.getppid()
        cmdline_path = pathlib.Path(f"/proc/{ppid}/cmdline")
        cmdline = cmdline_path.read_bytes().split(b"\0")
    except OSError:
        return False
    return any(b"sphinx-autobuild" in arg for arg in cmdline)


def detect_mode(
    *,
    config_value: str,
    argv: t.Sequence[str] | None = None,
    env: t.Mapping[str, str] | None = None,
    parent_check: t.Callable[[], bool] | None = None,
) -> Mode:
    """Resolve a ``sphinx_vite_builder_mode`` config value to a concrete :class:`Mode`.

    Parameters
    ----------
    config_value
        Raw value from ``conf.py``: ``"auto"``, ``"dev"``, or ``"prod"``.
        Anything else falls back to ``Mode.PROD`` (the safe / no-op
        default — never spawn a subprocess from a typo).
    argv
        Process argv. Defaults to :data:`sys.argv`.
    env
        Process environment. Defaults to :data:`os.environ`.
    parent_check
        Callable returning ``True`` when the parent process is
        ``sphinx-autobuild``. Defaults to
        :func:`_parent_is_sphinx_autobuild`. Tests pass ``lambda: False``
        to disable platform-specific behavior.

    Returns
    -------
    Mode
        The resolved mode. ``"auto"`` resolves to ``DEV`` if any of:
        - ``SPHINX_AUTOBUILD`` is set in ``env``
        - ``argv[0]`` ends with ``"sphinx-autobuild"``
        - the parent process is ``sphinx-autobuild`` (so the
          subprocess sphinx-autobuild spawns inherits the dev mode)
        ``PROD`` otherwise.

    Examples
    --------
    >>> detect_mode(
    ...     config_value="dev",
    ...     argv=["sphinx-build"],
    ...     env={},
    ...     parent_check=lambda: False,
    ... )
    <Mode.DEV: 'dev'>
    >>> detect_mode(
    ...     config_value="prod",
    ...     argv=["sphinx-autobuild"],
    ...     env={"SPHINX_AUTOBUILD": "1"},
    ...     parent_check=lambda: True,
    ... )
    <Mode.PROD: 'prod'>
    >>> detect_mode(
    ...     config_value="auto",
    ...     argv=["sphinx-build"],
    ...     env={},
    ...     parent_check=lambda: False,
    ... )
    <Mode.PROD: 'prod'>
    >>> detect_mode(
    ...     config_value="auto",
    ...     argv=["/p/sphinx-autobuild"],
    ...     env={},
    ...     parent_check=lambda: False,
    ... )
    <Mode.DEV: 'dev'>
    >>> detect_mode(
    ...     config_value="auto",
    ...     argv=["python"],
    ...     env={},
    ...     parent_check=lambda: True,
    ... )
    <Mode.DEV: 'dev'>
    """
    if config_value == "dev":
        return Mode.DEV
    if config_value == "prod":
        return Mode.PROD
    # "auto" or any unrecognised value falls through to detection.
    resolved_argv: t.Sequence[str] = argv if argv is not None else sys.argv
    resolved_env: t.Mapping[str, str] = env if env is not None else os.environ
    resolved_parent_check = (
        parent_check if parent_check is not None else _parent_is_sphinx_autobuild
    )

    if resolved_env.get("SPHINX_AUTOBUILD"):
        return Mode.DEV
    if resolved_argv and resolved_argv[0].endswith("sphinx-autobuild"):
        return Mode.DEV
    if resolved_parent_check():
        return Mode.DEV
    return Mode.PROD


def resolve_vite_root(explicit: str | os.PathLike[str] | None) -> pathlib.Path | None:
    """Resolve the ``sphinx_vite_builder_root`` config value to an absolute path.

    Returns ``None`` if no explicit root is set; the hook layer treats
    that as "no Vite project to spawn" and logs a debug message. We
    intentionally do not auto-detect the active theme's ``web/``
    directory here — auto-detection is brittle (depends on theme
    layout, which is theme-specific) and would couple this package to
    any one theme. Themes that want auto-wiring can set the config
    value themselves from their own ``setup()`` callback.

    Examples
    --------
    >>> resolve_vite_root(None) is None
    True
    >>> import pathlib
    >>> root = resolve_vite_root(pathlib.Path(__file__).parent)
    >>> root.is_absolute()
    True
    """
    if explicit is None:
        return None
    return pathlib.Path(explicit).resolve()


@dataclasses.dataclass(frozen=True, slots=True)
class SphinxViteBuilderConfig:
    """Frozen snapshot of the resolved sphinx-vite-builder configuration.

    Built once per Sphinx app at ``builder-inited`` time from
    ``app.config``; passed by value to the orchestration layer so the
    hooks don't carry a reference to the live mutable Sphinx config.
    """

    mode: Mode
    vite_root: pathlib.Path | None

    @property
    def should_spawn(self) -> bool:
        """True iff the orchestration layer should actually spawn Vite."""
        return self.mode is Mode.DEV and self.vite_root is not None
