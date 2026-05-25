"""sphinx-vite-builder — vite + pnpm orchestration for Sphinx-theme packages.

Two orthogonal entry points sharing one subprocess core:

1. **PEP 517 build backend** at :mod:`sphinx_vite_builder.build`. Runs
   ``pnpm exec vite build`` before delegating wheel/sdist construction
   to :mod:`hatchling.build`. Consumer packages declare it via
   ``[build-system].build-backend = "sphinx_vite_builder.build"``.
2. **Sphinx extension** registered by :func:`setup`. Hooks
   ``builder-inited`` to run ``pnpm exec vite build`` synchronously
   before Sphinx's ``copy_static_files`` phase.

Both heads consume the smart-subprocess core under
:mod:`sphinx_vite_builder._internal`.
"""

from __future__ import annotations

import logging
import typing as t

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

__version__ = "0.0.1a25"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register the Sphinx-extension head.

    Wires two config values (``sphinx_vite_builder_mode``,
    ``sphinx_vite_builder_root``) and connects the ``builder-inited``
    hook. The hook runs ``pnpm exec vite build`` synchronously;
    ``sphinx_vite_builder_root`` controls whether vite runs at all
    (unset → no-op, typical for installed wheels).

    Examples
    --------
    >>> class FakeApp:
    ...     def __init__(self) -> None:
    ...         self.config_values: list[str] = []
    ...         self.events: list[str] = []
    ...     def add_config_value(self, name: str, **kwargs: object) -> None:
    ...         self.config_values.append(name)
    ...     def connect(self, event: str, handler: object) -> None:
    ...         self.events.append(event)
    >>> fake = FakeApp()
    >>> metadata = setup(fake)  # type: ignore[arg-type]
    >>> "sphinx_vite_builder_mode" in fake.config_values
    True
    >>> "sphinx_vite_builder_root" in fake.config_values
    True
    >>> "builder-inited" in fake.events
    True
    >>> "build-finished" in fake.events
    True
    >>> metadata["parallel_read_safe"]
    True
    """
    from ._internal import hooks

    app.add_config_value(
        "sphinx_vite_builder_mode",
        default="auto",
        rebuild="env",
        types=[str],
    )
    app.add_config_value(
        "sphinx_vite_builder_root",
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


__all__: tuple[str, ...] = ("__version__", "setup")
