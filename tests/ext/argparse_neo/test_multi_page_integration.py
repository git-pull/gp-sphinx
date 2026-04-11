"""Integration test for multi-page duplicate-label scoping.

Builds a synthetic Sphinx project with two MyST pages that each embed an
``.. argparse::`` directive via ``{eval-rst}`` — matching the way downstream
consumers (vcspull, tmuxp, libtmux, …) wire up their CLI docs. Asserts that
the resulting build emits no ``duplicate label`` warnings for the shared
``usage`` / ``options`` / ``positional arguments`` section names.

See https://github.com/git-pull/gp-sphinx/issues/15.
"""

from __future__ import annotations

import io
import logging
import pathlib
import re
import sys
import textwrap
import typing as t

import pytest

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx


_PARSER_MOD = textwrap.dedent(
    """\
    from __future__ import annotations

    import argparse


    def create_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="myapp")
        sub = parser.add_subparsers(dest="command")

        add = sub.add_parser("add", help="Add a resource")
        add.add_argument("name", help="Name of the resource")
        add.add_argument("--force", action="store_true", help="Force overwrite")

        discover = sub.add_parser("discover", help="Scan for resources")
        discover.add_argument("path", help="Directory to scan")
        discover.add_argument("--depth", type=int, default=3, help="Recursion depth")

        return parser
    """,
)


_CONF_PY = textwrap.dedent(
    """\
    import sys
    sys.path.insert(0, r"{srcdir}")

    project = "argparse_neo_multipage"
    extensions = [
        "myst_parser",
        "sphinx_argparse_neo",
    ]
    master_doc = "index"
    exclude_patterns = ["_build"]
    html_theme = "alabaster"
    source_suffix = {{".md": "markdown"}}
    """,
)


_INDEX_MD = textwrap.dedent(
    """\
    # Multi-page argparse

    ```{toctree}
    :maxdepth: 1

    add
    discover
    ```
    """,
)


_ADD_MD = textwrap.dedent(
    """\
    # Add

    ```{eval-rst}
    .. argparse::
       :module: myapp_parser
       :func: create_parser
       :prog: myapp
       :path: add
    ```
    """,
)


_DISCOVER_MD = textwrap.dedent(
    """\
    # Discover

    ```{eval-rst}
    .. argparse::
       :module: myapp_parser
       :func: create_parser
       :prog: myapp
       :path: discover
    ```
    """,
)


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class _Result(t.NamedTuple):
    app: Sphinx
    warnings: str


def _purge_parser_module() -> None:
    for key in list(sys.modules):
        if key == "myapp_parser":
            del sys.modules[key]


def _build(tmp_path: pathlib.Path) -> _Result:
    from sphinx.application import Sphinx

    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    doctreedir = tmp_path / ".doctrees"
    srcdir.mkdir()
    outdir.mkdir()
    doctreedir.mkdir()

    (srcdir / "myapp_parser.py").write_text(_PARSER_MOD, encoding="utf-8")
    (srcdir / "conf.py").write_text(
        _CONF_PY.format(srcdir=str(srcdir)),
        encoding="utf-8",
    )
    (srcdir / "index.md").write_text(_INDEX_MD, encoding="utf-8")
    (srcdir / "add.md").write_text(_ADD_MD, encoding="utf-8")
    (srcdir / "discover.md").write_text(_DISCOVER_MD, encoding="utf-8")

    status_buf = io.StringIO()
    warning_buf = io.StringIO()

    # Snapshot the `sphinx` logger state before building. Sphinx.__init__
    # sets `sphinx.propagate = False` and attaches handlers that route events
    # into the provided warning/status streams. If we don't restore these,
    # subsequent tests that rely on `caplog` to capture sphinx-namespace
    # warnings (e.g. the SPF lint tests in tests/ext/pytest_fixtures/) see
    # empty records.
    sphinx_logger = logging.getLogger("sphinx")
    prev_propagate = sphinx_logger.propagate
    prev_handlers = list(sphinx_logger.handlers)
    prev_level = sphinx_logger.level

    _purge_parser_module()
    try:
        app = Sphinx(
            srcdir=str(srcdir),
            confdir=str(srcdir),
            outdir=str(outdir),
            doctreedir=str(doctreedir),
            buildername="html",
            status=status_buf,
            warning=warning_buf,
            freshenv=True,
        )
        app.build()
        return _Result(app=app, warnings=warning_buf.getvalue())
    finally:
        for h in list(sphinx_logger.handlers):
            if h not in prev_handlers:
                sphinx_logger.removeHandler(h)
        sphinx_logger.propagate = prev_propagate
        sphinx_logger.setLevel(prev_level)


def _duplicate_label_lines(warnings: str) -> list[str]:
    return [
        _ANSI.sub("", line)
        for line in warnings.splitlines()
        if "duplicate label" in line
    ]


@pytest.mark.integration
def test_multi_page_argparse_emits_no_duplicate_label_warnings(
    tmp_path: pathlib.Path,
) -> None:
    """Two MyST pages with ``.. argparse::`` must not collide on implicit targets.

    Regression test for https://github.com/git-pull/gp-sphinx/issues/15 —
    prior to the fix, ``section["names"]`` was left unscoped in
    ``render_usage_section`` / ``render_group_section``, so every CLI page
    produced identical ``usage`` / ``options`` / ``positional arguments``
    implicit targets and Sphinx's std domain logged one ``duplicate label``
    warning per collision.
    """
    result = _build(tmp_path)
    duplicates = _duplicate_label_lines(result.warnings)
    assert not duplicates, (
        "Unexpected duplicate-label warnings in build output:\n" + "\n".join(duplicates)
    )
