"""Integration test for the ``:no-index:`` flag on the argparse directive.

Builds a synthetic Sphinx project that renders one parser with ``:no-index:``
and verifies the card still renders (HTML anchors intact) while registering no
cross-reference targets: no ``argparse:*`` / ``std:cmdoption`` ``objects.inv``
entries, no ``std`` domain ``progoptions``, and no implicit section labels. This
lets a parser appear on more than one page with a single canonical xref home.
"""

from __future__ import annotations

import io
import pathlib
import re
import sys
import textwrap
import typing as t

import pytest
from sphinx.util.inventory import InventoryFile

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx


_PARSER_MOD = textwrap.dedent(
    """\
    from __future__ import annotations

    import argparse


    def create_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="myapp")
        parser.add_argument("-v", "--verbose", action="store_true", help="Verbose")
        parser.add_argument("filename", help="Input file")

        sub = parser.add_subparsers(dest="command")
        sync = sub.add_parser("sync", help="Synchronise")
        sync.add_argument("--force", action="store_true", help="Force sync")

        return parser
    """,
)


_CONF_PY = textwrap.dedent(
    """\
    import sys
    sys.path.insert(0, r"{srcdir}")

    project = "argparse_no_index"
    extensions = [
        "myst_parser",
        "sphinx_autodoc_argparse",
    ]
    master_doc = "index"
    exclude_patterns = ["_build"]
    html_theme = "alabaster"
    source_suffix = {{".md": "markdown"}}
    """,
)


_INDEX_MD = textwrap.dedent(
    """\
    # CLI Reference

    ```{eval-rst}
    .. argparse::
       :module: myparser
       :func: create_parser
       :prog: myapp
       :no-index:
    ```
    """,
)


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class _Result(t.NamedTuple):
    app: Sphinx
    warnings: str
    outdir: pathlib.Path


def _purge_parser_module() -> None:
    for key in list(sys.modules):
        if key == "myparser":
            del sys.modules[key]


def _build(tmp_path: pathlib.Path) -> _Result:
    from sphinx.application import Sphinx

    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    doctreedir = tmp_path / ".doctrees"
    srcdir.mkdir()
    outdir.mkdir()
    doctreedir.mkdir()

    (srcdir / "myparser.py").write_text(_PARSER_MOD, encoding="utf-8")
    (srcdir / "conf.py").write_text(
        _CONF_PY.format(srcdir=str(srcdir)),
        encoding="utf-8",
    )
    (srcdir / "index.md").write_text(_INDEX_MD, encoding="utf-8")

    status_buf = io.StringIO()
    warning_buf = io.StringIO()

    _purge_parser_module()

    app = Sphinx(
        srcdir=str(srcdir),
        confdir=str(srcdir),
        outdir=str(outdir),
        doctreedir=str(doctreedir),
        buildername="html",
        freshenv=True,
        status=status_buf,
        warning=warning_buf,
    )
    app.build()

    warnings = _ANSI.sub("", warning_buf.getvalue())
    return _Result(app=app, warnings=warnings, outdir=outdir)


def _load_inventory(outdir: pathlib.Path) -> dict[str, dict[str, t.Any]]:
    inv_path = outdir / "objects.inv"
    with inv_path.open("rb") as handle:
        return InventoryFile.load(handle, "", lambda base, target: target)


@pytest.fixture(scope="module")
def no_index_result(tmp_path_factory: pytest.TempPathFactory) -> _Result:
    """Build a Sphinx project with a ``:no-index:`` argparse directive."""
    return _build(tmp_path_factory.mktemp("argparse-no-index"))


@pytest.mark.integration
def test_no_index_registers_no_argparse_domain_entries(
    no_index_result: _Result,
) -> None:
    """No ``argparse:*`` cross-reference targets land in objects.inv."""
    inventory = _load_inventory(no_index_result.outdir)
    argparse_domains = [
        domain for domain in inventory if domain.startswith("argparse:")
    ]
    assert argparse_domains == []


@pytest.mark.integration
def test_no_index_registers_no_std_cmdoption(no_index_result: _Result) -> None:
    """No ``std:cmdoption`` entries and an empty std-domain progoptions table."""
    inventory = _load_inventory(no_index_result.outdir)
    assert inventory.get("std:cmdoption", {}) == {}

    std_domain = no_index_result.app.env.domains.standard_domain
    assert dict(std_domain.progoptions) == {}


@pytest.mark.integration
def test_no_index_still_renders_the_card(no_index_result: _Result) -> None:
    """The parser still renders with per-section HTML anchors."""
    index_html = (no_index_result.outdir / "index.html").read_text(encoding="utf-8")
    assert "Usage" in index_html
    assert 'id="usage"' in index_html
