"""Mode detection + config dataclass for gp-sphinx-vite.

Pure functions where possible — keeps the unit tests cheap (no Sphinx
fixture, no subprocess). The Sphinx-aware glue lives in :mod:`hooks`.

The mode detection mirrors what Furo's `_builder_inited` does indirectly
(check builder name + extensions list); we additionally inspect ``argv``
and ``SPHINX_AUTOBUILD`` so the orchestration becomes a no-op for
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


def detect_mode(
    *,
    config_value: str,
    argv: t.Sequence[str] | None = None,
    env: t.Mapping[str, str] | None = None,
) -> Mode:
    """Resolve a ``gp_sphinx_vite_mode`` config value to a concrete :class:`Mode`.

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

    Returns
    -------
    Mode
        The resolved mode. ``"auto"`` resolves to ``DEV`` if either
        ``SPHINX_AUTOBUILD`` is set in ``env`` or ``argv[0]`` ends with
        ``"sphinx-autobuild"``; ``PROD`` otherwise.

    Examples
    --------
    >>> detect_mode(config_value="dev", argv=["sphinx-build"], env={})
    <Mode.DEV: 'dev'>
    >>> detect_mode(
    ...     config_value="prod",
    ...     argv=["sphinx-autobuild"],
    ...     env={"SPHINX_AUTOBUILD": "1"},
    ... )
    <Mode.PROD: 'prod'>
    >>> detect_mode(config_value="auto", argv=["sphinx-build"], env={})
    <Mode.PROD: 'prod'>
    >>> detect_mode(config_value="auto", argv=["/p/sphinx-autobuild"], env={})
    <Mode.DEV: 'dev'>
    >>> detect_mode(
    ...     config_value="auto",
    ...     argv=["sphinx-build"],
    ...     env={"SPHINX_AUTOBUILD": "1"},
    ... )
    <Mode.DEV: 'dev'>
    >>> detect_mode(config_value="garbage", argv=[], env={})
    <Mode.PROD: 'prod'>
    """
    if config_value == "dev":
        return Mode.DEV
    if config_value == "prod":
        return Mode.PROD
    # "auto" or any unrecognised value falls through to detection.
    resolved_argv: t.Sequence[str] = argv if argv is not None else sys.argv
    resolved_env: t.Mapping[str, str] = env if env is not None else os.environ

    if resolved_env.get("SPHINX_AUTOBUILD"):
        return Mode.DEV
    if resolved_argv and resolved_argv[0].endswith("sphinx-autobuild"):
        return Mode.DEV
    return Mode.PROD


def resolve_vite_root(explicit: str | os.PathLike[str] | None) -> pathlib.Path | None:
    """Resolve the ``gp_sphinx_vite_root`` config value to an absolute path.

    Returns ``None`` if no explicit root is set; the hook layer treats
    that as "no Vite project to spawn" and logs a debug message. We
    intentionally do not auto-detect the active theme's ``web/``
    directory here — auto-detection is brittle (depends on theme
    layout, which is theme-specific) and would couple this package to
    gp-furo-theme. Themes that want auto-wiring can set the config
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
class GpSphinxViteConfig:
    """Frozen snapshot of the resolved gp-sphinx-vite configuration.

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
