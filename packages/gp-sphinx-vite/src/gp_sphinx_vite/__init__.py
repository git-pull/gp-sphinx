"""gp-sphinx-vite — transparent Vite/pnpm orchestration for Sphinx themes.

Spawns ``pnpm exec vite build --watch`` from a Sphinx ``builder-inited``
hook so a theme author iterating templates + SCSS gets fresh CSS/JS on
disk without remembering a separate ``vite build`` invocation. The
extension is a no-op in production (when ``sphinx-build`` runs without
the autobuild driver), so wheels published to PyPI never carry a Node
runtime requirement.

This file is the package skeleton — :func:`setup` registers the config
value(s) and a placeholder hook. Subprocess orchestration
(``ViteProcess``), the asyncio↔threading bridge, and the actual
spawn/teardown lifecycle land in subsequent commits.

Examples
--------
>>> class FakeApp:
...     def __init__(self) -> None:
...         self.config_values: list[str] = []
...     def add_config_value(self, name: str, **kwargs: object) -> None:
...         self.config_values.append(name)
>>> fake = FakeApp()
>>> metadata = setup(fake)  # type: ignore[arg-type]
>>> "gp_sphinx_vite_mode" in fake.config_values
True
>>> metadata["parallel_read_safe"]
True
"""

from __future__ import annotations

import logging
import typing as t

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

__version__ = "0.0.1a16.dev2"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def setup(app: Sphinx) -> dict[str, bool | str]:
    """Register ``gp-sphinx-vite``'s config values + event handlers with Sphinx.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application object.

    Returns
    -------
    dict[str, bool | str]
        Extension metadata. ``parallel_read_safe`` and
        ``parallel_write_safe`` are both ``True``: the orchestration is
        a side effect of one specific event handler firing, and the
        rest of the extension is read-only state.
    """
    from . import hooks

    app.add_config_value(
        "gp_sphinx_vite_mode",
        default="auto",
        rebuild="env",
        types=[str],
    )
    app.add_config_value(
        "gp_sphinx_vite_root",
        default=None,
        rebuild="env",
        types=[str, type(None)],
    )

    app.connect("builder-inited", hooks.on_builder_inited)
    app.connect("build-finished", hooks.on_build_finished)

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": __version__,
    }
