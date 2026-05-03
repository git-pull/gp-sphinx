"""Hatchling build-hook variant of the vite orchestration.

Consumers who keep ``build-backend = "hatchling.build"`` can opt in to
the same vite-build-before-package behaviour the
:mod:`sphinx_vite_builder.build` PEP 517 backend provides, by adding:

.. code-block:: toml

    [build-system]
    requires = ["hatchling>=1.0", "sphinx-vite-builder"]
    build-backend = "hatchling.build"

    [tool.hatch.build.hooks.vite]

…to their ``pyproject.toml``. Hatchling discovers this module via the
``[project.entry-points.hatch] vite = "sphinx_vite_builder.hatch_plugin"``
registration in *this* package's ``pyproject.toml``; the
:func:`hatch_register_build_hook` hookimpl returns the
:class:`ViteBuildHook` class.

The hook reuses :func:`sphinx_vite_builder._internal.vite.run_vite_build`
verbatim — same SKIP env-var, same ``web/``-absent short-circuit, same
fast-fail diagnostics (``PnpmMissingError``, ``NodeModulesInstallError``,
``ViteFailedError``). The two activation paths are mutually exclusive
by ``[build-system].build-backend`` (you can't pick both at once), so
no double-vite invocation is possible.
"""

from __future__ import annotations

import pathlib
import typing as t

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl

from ._internal.vite import run_vite_build


class ViteBuildHook(BuildHookInterface[t.Any]):
    """Run ``pnpm exec vite build`` before each hatchling build target.

    Activated via ``[tool.hatch.build.hooks.vite]`` in a consumer's
    ``pyproject.toml``; the table key (``vite``) must match
    :attr:`PLUGIN_NAME` so hatchling can route the config block.

    Examples
    --------
    The class declares the canonical ``PLUGIN_NAME`` hatchling looks
    up when matching ``[tool.hatch.build.hooks.<name>]`` to a
    discovered hook. The name is part of the public contract — changing
    it would break existing consumer ``pyproject.toml`` configurations.

    >>> ViteBuildHook.PLUGIN_NAME
    'vite'
    """

    PLUGIN_NAME = "vite"

    def initialize(self, version: str, build_data: dict[str, t.Any]) -> None:
        """Run vite once before hatchling assembles ``version``'s artefact.

        Delegates to :func:`run_vite_build` so the SKIP env-var,
        ``web/``-absent short-circuit, and fast-fail diagnostics behave
        identically to the PEP 517 backend variant.
        """
        del version, build_data
        run_vite_build(project_root=pathlib.Path(self.root))


@hookimpl
def hatch_register_build_hook() -> list[type[BuildHookInterface[t.Any]]]:
    """Hatchling plugin entry point.

    Discovered via the ``[project.entry-points.hatch] vite = ...``
    registration in this package's ``pyproject.toml``. Returns hook
    classes (not instances); hatchling instantiates them per build.

    Examples
    --------
    The function returns exactly one hook class so the
    ``[tool.hatch.build.hooks.vite]`` table key resolves to
    :class:`ViteBuildHook`:

    >>> hooks = hatch_register_build_hook()
    >>> [hook.PLUGIN_NAME for hook in hooks]
    ['vite']
    """
    return [ViteBuildHook]


__all__: tuple[str, ...] = ("ViteBuildHook", "hatch_register_build_hook")
