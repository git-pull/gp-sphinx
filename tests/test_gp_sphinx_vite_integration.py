"""Integration test: gp_sphinx_vite wired into a real Sphinx build.

Exercises the full path — entry-point loaded from the Sphinx
extensions list, ``setup()`` invoked, ``builder-inited`` fires, the
hook spawns ViteProcess against a fake-vite script, ``build-finished``
fires (no-op), and the test explicitly tears down. The unit tests in
``test_gp_sphinx_vite_hooks.py`` cover the same surface against a
hand-rolled FakeApp; this file proves the wiring through Sphinx itself.

Skipped in CI environments that scrub Python interpreters from PATH —
the fake vite is just ``sys.executable`` running an inline script.
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
    """Build a conf.py that wires gp_sphinx_vite + monkey-patches the watch command.

    The monkey-patch happens at conf.py time (which runs before
    builder-inited fires), via ``gp_sphinx_vite.process.vite_watch_command``
    being replaced. The hook reads it from
    ``gp_sphinx_vite.hooks.vite_watch_command`` (its own module-level
    rebinding done at import time), so we patch *that* name.
    """
    return textwrap.dedent(
        f"""\
        import gp_sphinx_vite.hooks
        gp_sphinx_vite.hooks.vite_watch_command = lambda: {fake_vite_argv!r}

        extensions = ["gp_sphinx_vite"]
        html_theme = "basic"
        master_doc = "index"
        project = "integration demo"
        gp_sphinx_vite_mode = "dev"
        gp_sphinx_vite_root = {fake_vite_root!r}
        """,
    )


@pytest.mark.integration
def test_sphinx_build_spawns_via_extension(tmp_path: pathlib.Path) -> None:
    """A Sphinx build with the extension active spawns the watch process."""
    fake_vite_dir = tmp_path / "fake-vite-root"
    fake_vite_dir.mkdir()
    (fake_vite_dir / "package.json").write_text('{"name": "fake-vite-integration"}\n')
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
        purge_modules=("gp_sphinx_vite", "gp_sphinx_vite.hooks"),
    )

    proc = getattr(result.app, "_gp_sphinx_vite_proc", None)
    bus = getattr(result.app, "_gp_sphinx_vite_bus", None)
    try:
        assert proc is not None, "hooks did not stash a ViteProcess on the app"
        assert bus is not None, "hooks did not stash an AsyncioBus on the app"
        assert proc.is_running, "ViteProcess exited before the test could observe it"
        assert bus.is_running, "AsyncioBus stopped before the test could observe it"
    finally:
        # Explicit teardown — atexit-based cleanup runs at interpreter
        # exit, which is fine for production but leaves the test
        # process holding the bus thread until then.
        from gp_sphinx_vite import hooks

        hooks.teardown(result.app, terminate_timeout=2.0)


@pytest.mark.integration
def test_sphinx_build_no_op_in_prod_mode(tmp_path: pathlib.Path) -> None:
    """`gp_sphinx_vite_mode = "prod"` builds without spawning anything."""
    scenario = SphinxScenario(
        files=(
            ScenarioFile(
                "conf.py",
                textwrap.dedent(
                    """\
                    extensions = ["gp_sphinx_vite"]
                    html_theme = "basic"
                    master_doc = "index"
                    project = "no-op demo"
                    gp_sphinx_vite_mode = "prod"
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
        purge_modules=("gp_sphinx_vite",),
    )
    assert getattr(result.app, "_gp_sphinx_vite_proc", None) is None
    assert getattr(result.app, "_gp_sphinx_vite_bus", None) is None
