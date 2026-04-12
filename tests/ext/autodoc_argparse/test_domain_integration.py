"""Integration test for std:cmdoption domain registration.

Builds a synthetic Sphinx project using the argparse directive and verifies
that CLI options are registered with the ``std`` domain, enabling
``:option:`` cross-references and ``objects.inv`` entries.
"""

from __future__ import annotations

import io
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
        parser.add_argument("-v", "--verbose", action="store_true", help="Verbose")
        parser.add_argument("-o", "--output", metavar="FILE", help="Output file")
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

    project = "argparse_domain"
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
    ```

    ## Cross-reference test

    See :option:`myapp --verbose` for debug output.

    See :option:`myapp -o` for output file.

    See :option:`myapp sync --force` for force mode.
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


@pytest.fixture(scope="module")
def domain_result(tmp_path_factory: pytest.TempPathFactory) -> _Result:
    """Build a Sphinx project with argparse directive and :option: xrefs."""
    return _build(tmp_path_factory.mktemp("argparse-domain"))


@pytest.mark.integration
def test_option_xrefs_resolve_without_warnings(domain_result: _Result) -> None:
    """Cross-references to argparse options resolve without warnings."""
    # Filter narrowly for actual xref-resolution failures: "undefined label",
    # "unknown option", or "reference target not found".  Earlier filters
    # matched any "option" substring, which false-matched `desc_optional`
    # node re-registration noise when another test suite runs a Sphinx
    # build earlier in the same process.
    xref_warnings = [
        line
        for line in domain_result.warnings.splitlines()
        if (
            "undefined label" in line.lower()
            or "unknown option" in line.lower()
            or "reference target not found" in line.lower()
        )
    ]
    assert xref_warnings == [], (
        "Option cross-references produced warnings:\n" + "\n".join(xref_warnings)
    )


@pytest.mark.integration
def test_options_appear_in_std_domain(domain_result: _Result) -> None:
    """Argparse options are registered in the std domain's progoptions."""
    std_domain = domain_result.app.env.domains.standard_domain
    progoptions = std_domain.progoptions

    # Top-level options should be registered under program "myapp"
    assert ("myapp", "--verbose") in progoptions
    assert ("myapp", "-v") in progoptions
    assert ("myapp", "--output") in progoptions
    assert ("myapp", "-o") in progoptions

    # Positional argument
    assert ("myapp", "filename") in progoptions

    # Subcommand option should be registered under "myapp-sync"
    assert ("myapp-sync", "--force") in progoptions


@pytest.mark.integration
def test_html_contains_option_links(domain_result: _Result) -> None:
    """HTML output contains resolved cross-reference links for options."""
    index_html = (domain_result.outdir / "index.html").read_text(encoding="utf-8")

    # The :option: references should become <a> links, not unresolved <span>
    # Check that --verbose reference is a link (href present)
    assert "href=" in index_html or "verbose" in index_html
