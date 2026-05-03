"""PEP 517 / PEP 660 build backend module.

Consumer ``pyproject.toml`` references this module via:

.. code-block:: toml

    [build-system]
    requires = ["hatchling>=1.0", "sphinx-vite-builder"]
    build-backend = "sphinx_vite_builder.build"
    backend-path = ["../sphinx-vite-builder/src"]    # for in-tree workspace builds

Each PEP 517 hook runs :func:`run_vite_build` to populate the consumer
package's vite-managed ``static/`` tree, then delegates to
:mod:`hatchling.build` for the actual sdist / wheel / editable
construction. The hooks are pure functions, defined at module scope,
mirroring the canonical layout of `flit_core.buildapi` and
`hatchling.build`.

Optional hooks (``get_requires_for_build_*`` and
``prepare_metadata_for_build_*``) are aliased verbatim to hatchling's
implementations — vite has no influence on dependency resolution or
distribution metadata, so passing those calls through unmodified is
both correct and trivially side-effect-free.
"""

from __future__ import annotations

import typing as t

import hatchling.build as _hatchling

from ._internal.vite import run_vite_build


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, t.Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """PEP 517 ``build_wheel``: vite-build, then hatchling-pack.

    Examples
    --------
    The hook's signature is the canonical PEP 517 shape consumers
    expect:

    >>> import inspect
    >>> sorted(inspect.signature(build_wheel).parameters)
    ['config_settings', 'metadata_directory', 'wheel_directory']
    >>> callable(build_wheel)
    True
    """
    run_vite_build()
    return _hatchling.build_wheel(wheel_directory, config_settings, metadata_directory)


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, t.Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """PEP 660 ``build_editable``: vite-build, then hatchling-pack-editable.

    Examples
    --------
    >>> import inspect
    >>> sorted(inspect.signature(build_editable).parameters)
    ['config_settings', 'metadata_directory', 'wheel_directory']
    >>> callable(build_editable)
    True
    """
    run_vite_build()
    return _hatchling.build_editable(
        wheel_directory, config_settings, metadata_directory
    )


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, t.Any] | None = None,
) -> str:
    """PEP 517 ``build_sdist``: pre-bake static so the sdist→wheel chain works.

    Running vite at sdist-build time means the resulting ``.tar.gz``
    contains a populated ``static/`` tree (even though the source repo
    gitignores it). Downstream consumers can then ``pip install`` from
    the sdist without pnpm or Node — the wheel-from-sdist build will
    skip vite (no ``web/`` in the unpacked tree) and ship the
    pre-baked assets via hatchling's normal file selection.

    Examples
    --------
    >>> import inspect
    >>> sorted(inspect.signature(build_sdist).parameters)
    ['config_settings', 'sdist_directory']
    >>> callable(build_sdist)
    True
    """
    run_vite_build()
    return _hatchling.build_sdist(sdist_directory, config_settings)


# The optional hooks have no vite-side concern — pass through verbatim.
# Keeping them as module-level aliases (rather than wrapping functions)
# preserves their identity for build frontends that introspect the
# module surface.
get_requires_for_build_wheel = _hatchling.get_requires_for_build_wheel
get_requires_for_build_sdist = _hatchling.get_requires_for_build_sdist
get_requires_for_build_editable = _hatchling.get_requires_for_build_editable
prepare_metadata_for_build_wheel = _hatchling.prepare_metadata_for_build_wheel
prepare_metadata_for_build_editable = _hatchling.prepare_metadata_for_build_editable


__all__: tuple[str, ...] = (
    "build_editable",
    "build_sdist",
    "build_wheel",
    "get_requires_for_build_editable",
    "get_requires_for_build_sdist",
    "get_requires_for_build_wheel",
    "prepare_metadata_for_build_editable",
    "prepare_metadata_for_build_wheel",
)
