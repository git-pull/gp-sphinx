"""Integration test: sphinx_vite_builder wired into a real Sphinx build.

Exercises the full path — entry-point loaded from the Sphinx extensions
list, ``setup()`` invoked, ``builder-inited`` fires, the hook spawns
:class:`AsyncProcess` against a fake-vite script, ``build-finished`` fires
(no-op), and the test explicitly tears down. The unit tests in
``test_sphinx_vite_builder_hooks.py`` cover the same surface against a
hand-rolled FakeApp; this file proves the wiring through Sphinx itself.
"""

from __future__ import annotations

import shutil
import sys
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


pytestmark = pytest.mark.skipif(
    shutil.which(sys.executable.split("/")[-1]) is None and not sys.executable,
    reason="No Python interpreter found on PATH for the fake-vite child",
)


_INDEX_RST = textwrap.dedent(
    """\
    Integration Demo
    ================

    Hello.
    """,
)


def _conf_py(*, fake_vite_root: str, fake_vite_argv: tuple[str, ...]) -> str:
    """Build a conf.py that wires sphinx_vite_builder + monkey-patches the watch.

    The monkey-patch happens at conf.py time (which runs before
    builder-inited fires), via
    ``sphinx_vite_builder._internal.hooks.vite_watch_command`` being
    replaced. The hook reads it from its own module-level rebinding done
    at import time, so we patch *that* name.
    """
    return textwrap.dedent(
        f"""\
        import sphinx_vite_builder._internal.hooks as _svb_hooks
        _svb_hooks.vite_watch_command = lambda: {fake_vite_argv!r}

        extensions = ["sphinx_vite_builder"]
        html_theme = "basic"
        master_doc = "index"
        project = "integration demo"
        sphinx_vite_builder_mode = "dev"
        sphinx_vite_builder_root = {fake_vite_root!r}
        """,
    )


@pytest.mark.integration
def test_sphinx_build_spawns_via_extension(tmp_path: pathlib.Path) -> None:
    """A Sphinx build with the extension active spawns the watch process."""
    fake_vite_dir = tmp_path / "fake-vite-root"
    fake_vite_dir.mkdir()
    (fake_vite_dir / "package.json").write_text('{"name": "fake-vite-integration"}\n')
    # Pre-create node_modules/ so _ensure_node_modules short-circuits the
    # auto-install path (CI runners don't have pnpm on PATH).
    (fake_vite_dir / "node_modules").mkdir()
    fake_script = fake_vite_dir / "fake_vite.py"
    fake_script.write_text(
        textwrap.dedent(
            """\
            import time
            print("vite ready", flush=True)
            while True:
                time.sleep(0.1)
            """,
        ),
    )

    fake_vite_argv = (sys.executable, str(fake_script))
    scenario = SphinxScenario(
        files=(
            ScenarioFile(
                "conf.py",
                _conf_py(
                    fake_vite_root=str(fake_vite_dir),
                    fake_vite_argv=fake_vite_argv,
                ),
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

    proc = getattr(result.app, "_sphinx_vite_builder_proc", None)
    bus = getattr(result.app, "_sphinx_vite_builder_bus", None)
    try:
        assert proc is not None, "hooks did not stash an AsyncProcess on the app"
        assert bus is not None, "hooks did not stash an AsyncioBus on the app"
        assert proc.is_running, "AsyncProcess exited before the test could observe it"
        assert bus.is_running, "AsyncioBus stopped before the test could observe it"
    finally:
        # Explicit teardown — atexit-based cleanup runs at interpreter
        # exit, which is fine for production but leaves the test
        # process holding the bus thread until then.
        from sphinx_vite_builder._internal import hooks

        hooks.teardown(result.app, terminate_timeout=2.0)


@pytest.mark.integration
def test_sphinx_build_no_op_in_prod_mode(tmp_path: pathlib.Path) -> None:
    """`sphinx_vite_builder_mode = "prod"` builds without spawning anything."""
    scenario = SphinxScenario(
        files=(
            ScenarioFile(
                "conf.py",
                textwrap.dedent(
                    """\
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

    result: SharedSphinxResult = build_isolated_sphinx_result(
        cache_root=tmp_path / "scenario-cache",
        tmp_path=tmp_path / "scenario-tmp",
        scenario=scenario,
        purge_modules=("sphinx_vite_builder",),
    )
    assert getattr(result.app, "_sphinx_vite_builder_proc", None) is None
    assert getattr(result.app, "_sphinx_vite_builder_bus", None) is None
