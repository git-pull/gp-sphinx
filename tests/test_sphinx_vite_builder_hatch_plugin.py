"""Tests for :mod:`sphinx_vite_builder.hatch_plugin`.

Validates the Phase-3 Milestone-A hatchling build-hook variant: that
the hook class declares the expected plugin name, that the registration
hookimpl returns it, that ``initialize()`` delegates to
:func:`run_vite_build`, and that the ``[tool.hatch.build.hooks.vite]``
activation path produces a working wheel against a synthetic project
when the SKIP env-var is set.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap

import pytest
from sphinx_vite_builder import hatch_plugin
from sphinx_vite_builder.hatch_plugin import (
    ViteBuildHook,
    hatch_register_build_hook,
)


def test_plugin_name_is_vite() -> None:
    """``PLUGIN_NAME`` must match the consumer's ``[tool.hatch.build.hooks.<name>]``."""
    assert ViteBuildHook.PLUGIN_NAME == "vite"


def test_hatch_register_build_hook_returns_class() -> None:
    """Registration hookimpl returns the hook class (not an instance)."""
    hooks = hatch_register_build_hook()
    assert hooks == [ViteBuildHook]
    # Sanity: hatchling instantiates the class per build, so it must
    # really be a class — not a callable, not an already-built instance.
    assert isinstance(hooks[0], type)


def test_initialize_invokes_run_vite_build(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """``initialize()`` calls ``run_vite_build`` with the project root."""
    captured: list[pathlib.Path] = []

    def _fake_run_vite_build(
        project_root: pathlib.Path | None = None,
        *,
        package_manager: str = "pnpm",
    ) -> None:
        del package_manager
        assert project_root is not None
        captured.append(project_root)

    monkeypatch.setattr(hatch_plugin, "run_vite_build", _fake_run_vite_build)

    # Hatchling's BuildHookInterface constructor takes a root plus
    # several other positional args (config, build_config, metadata,
    # directory, target_name); pass `None` for the slots initialize()
    # doesn't touch. The real per-build construction path is exercised
    # by the synthetic-project test below.
    hook = ViteBuildHook(
        root=str(tmp_path),
        config={},
        build_config=None,  # type: ignore[arg-type]
        metadata=None,  # type: ignore[arg-type]
        directory="",
        target_name="wheel",
    )
    hook.initialize("0.0.0", build_data={})

    assert captured == [tmp_path]


def test_entry_point_is_discoverable() -> None:
    """The ``hatch`` entry-point group exposes the registration hookimpl.

    Hatchling discovers plugins via ``importlib.metadata.entry_points
    (group="hatch")`` (per ``hatchling/plugin/manager.py:load``); the
    entry point declared in this package's ``pyproject.toml`` must
    resolve to a callable returning the hook class.
    """
    import importlib.metadata as ilm

    eps = ilm.entry_points(group="hatch")
    matched = [ep for ep in eps if ep.name == "vite"]
    assert matched, "vite entry point not registered in hatch group"
    module = matched[0].load()
    assert hasattr(module, "hatch_register_build_hook"), (
        "loaded entry point lacks hatch_register_build_hook hookimpl"
    )
    hooks = module.hatch_register_build_hook()
    # Compare by module-and-qualname rather than by object identity:
    # pytest's `--doctest-modules` and the entry-point loader can each
    # reach the same ViteBuildHook source file via different sys.modules
    # paths, producing two distinct class objects that satisfy the
    # contract but fail an `in` membership test against the test
    # module's own import.
    assert any(
        hook.__module__ == ViteBuildHook.__module__
        and hook.__qualname__ == ViteBuildHook.__qualname__
        for hook in hooks
    )


@pytest.mark.integration
def test_synthetic_project_builds_via_hatch_hook(tmp_path: pathlib.Path) -> None:
    """End-to-end: a synthetic project with the hook activated builds a wheel.

    Mirrors the SKIP-env-var doctest pattern from
    ``sphinx_vite_builder.build.build_wheel`` but exercises the
    hatchling-hook activation path instead of the PEP 517 backend
    swap. Sets ``SPHINX_VITE_BUILDER_SKIP=1`` so the test never needs
    pnpm or Node on PATH.
    """
    project = tmp_path / "doctest_pkg"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        textwrap.dedent(
            """\
            [build-system]
            requires = ["hatchling"]
            build-backend = "hatchling.build"

            [project]
            name = "synthetic-vite-hook-pkg"
            version = "0.0.0"

            [tool.hatch.build.hooks.vite]

            [tool.hatch.build.targets.wheel]
            packages = ["synthetic_pkg"]
            """,
        ),
    )
    pkg = project / "synthetic_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    dist = project / "dist"
    dist.mkdir()

    env = dict(os.environ)
    env["SPHINX_VITE_BUILDER_SKIP"] = "1"

    with tempfile.TemporaryDirectory() as build_temp:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    f"""\
                    import os
                    os.chdir({str(project)!r})
                    from hatchling.build import build_wheel
                    name = build_wheel({str(dist)!r})
                    print(name)
                    """,
                ),
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=build_temp,
            check=False,
        )

    assert result.returncode == 0, (
        f"hatch wheel build failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    wheels = list(dist.glob("*.whl"))
    assert len(wheels) == 1, f"expected 1 wheel, got {wheels}"


def test_top_level_exports() -> None:
    """The module's public surface is the hook class + the hookimpl."""
    assert "ViteBuildHook" in hatch_plugin.__all__
    assert "hatch_register_build_hook" in hatch_plugin.__all__
