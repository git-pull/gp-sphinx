"""Integration test: sphinx_vite_builder wired into a real Sphinx build.

Exercises the full path — entry-point loaded from the Sphinx extensions
list, ``setup()`` invoked, ``builder-inited`` fires and runs the
synchronous vite build (monkey-patched here to a no-op recorder),
``build-finished`` fires (no-op). The unit tests in
``test_sphinx_vite_builder_hooks.py`` cover the same surface against a
hand-rolled FakeApp; this file proves the wiring through Sphinx itself.
"""

from __future__ import annotations

import textwrap
import typing as t

import pytest

from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_isolated_sphinx_result,
)

if t.TYPE_CHECKING:
    import pathlib


_INDEX_RST = textwrap.dedent(
    """\
    Integration Demo
    ================

    Hello.
    """,
)


def _conf_py_with_recorder(*, fake_vite_root: str) -> str:
    """Build a conf.py that wires sphinx_vite_builder and records vite calls.

    Replaces ``sphinx_vite_builder._internal.hooks.run_vite_build`` with
    a recorder that appends to ``_recorded_vite_calls`` on the module,
    so the test can verify the hook actually fired without spawning a
    real subprocess.
    """
    return textwrap.dedent(
        f"""\
        import sphinx_vite_builder._internal.hooks as _svb_hooks

        _svb_hooks._recorded_vite_calls = []

        def _recorder(*, project_root):
            _svb_hooks._recorded_vite_calls.append(project_root)

        _svb_hooks.run_vite_build = _recorder

        extensions = ["sphinx_vite_builder"]
        html_theme = "basic"
        master_doc = "index"
        project = "integration demo"
        sphinx_vite_builder_mode = "dev"
        sphinx_vite_builder_root = {fake_vite_root!r}
        """,
    )


@pytest.mark.integration
def test_sphinx_build_runs_vite_build_via_extension(tmp_path: pathlib.Path) -> None:
    """A Sphinx build with the extension active calls ``run_vite_build``."""
    fake_vite_dir = tmp_path / "fake-vite-root"
    fake_vite_dir.mkdir()

    scenario = SphinxScenario(
        files=(
            ScenarioFile(
                "conf.py",
                _conf_py_with_recorder(fake_vite_root=str(fake_vite_dir)),
            ),
            ScenarioFile("index.rst", _INDEX_RST),
        ),
    )

    result: SharedSphinxResult = build_isolated_sphinx_result(
        cache_root=tmp_path / "scenario-cache",
        tmp_path=tmp_path / "scenario-tmp",
        scenario=scenario,
        purge_modules=(
            "sphinx_vite_builder",
            "sphinx_vite_builder._internal",
            "sphinx_vite_builder._internal.hooks",
        ),
    )

    from sphinx_vite_builder._internal import hooks

    calls = getattr(hooks, "_recorded_vite_calls", None)
    assert calls is not None, "conf.py recorder did not initialise"
    assert len(calls) >= 1, "run_vite_build was not invoked by the extension"
    # ``sphinx_vite_builder_root`` was the fake_vite_dir (the ``web/``
    # equivalent); the hook should pass its *parent* as project_root.
    assert calls[0] == fake_vite_dir.parent

    # Sphinx build itself should still succeed.
    assert result.app is not None


@pytest.mark.integration
def test_sphinx_build_no_op_when_root_unset(tmp_path: pathlib.Path) -> None:
    """Without ``sphinx_vite_builder_root`` the build skips vite entirely."""
    scenario = SphinxScenario(
        files=(
            ScenarioFile(
                "conf.py",
                textwrap.dedent(
                    """\
                    import sphinx_vite_builder._internal.hooks as _svb_hooks

                    _svb_hooks._recorded_vite_calls = []

                    def _recorder(*, project_root):
                        _svb_hooks._recorded_vite_calls.append(project_root)

                    _svb_hooks.run_vite_build = _recorder

                    extensions = ["sphinx_vite_builder"]
                    html_theme = "basic"
                    master_doc = "index"
                    project = "no-op demo"
                    sphinx_vite_builder_mode = "prod"
                    """,
                ),
            ),
            ScenarioFile("index.rst", _INDEX_RST),
        ),
    )

    build_isolated_sphinx_result(
        cache_root=tmp_path / "scenario-cache",
        tmp_path=tmp_path / "scenario-tmp",
        scenario=scenario,
        purge_modules=("sphinx_vite_builder",),
    )

    from sphinx_vite_builder._internal import hooks

    assert getattr(hooks, "_recorded_vite_calls", []) == []
