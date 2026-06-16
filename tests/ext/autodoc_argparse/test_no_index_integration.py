"""Integration test for the ``:no-index:`` flag on the argparse directive.

Builds a synthetic Sphinx project that renders one parser with ``:no-index:``
and verifies the card still renders (HTML anchors intact) while registering no
cross-reference targets: no ``argparse:*`` / ``std:cmdoption`` ``objects.inv``
entries, no ``std`` domain ``progoptions``, and no implicit section labels. This
lets a parser appear on more than one page with a single canonical xref home.
"""

from __future__ import annotations

import textwrap
import typing as t

import pytest
from sphinx.util.inventory import InventoryFile

from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

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
    """
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations
    import sys
    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    project = "argparse_no_index"
    extensions = [
        "myst_parser",
        "sphinx_autodoc_argparse",
    ]
    """
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
    """
)


def _load_inventory(result: SharedSphinxResult) -> dict[str, dict[str, t.Any]]:
    """Parse the built ``objects.inv`` into ``{domain: {name: item}}``."""
    inv_path = result.outdir / "objects.inv"
    with inv_path.open("rb") as handle:
        return InventoryFile.load(handle, "", lambda base, target: target)


@pytest.fixture(scope="module")
def no_index_result(tmp_path_factory: pytest.TempPathFactory) -> SharedSphinxResult:
    """Build a Sphinx project with a ``:no-index:`` argparse directive."""
    cache_root = tmp_path_factory.mktemp("argparse-no-index")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("myparser.py", _PARSER_MOD),
            ScenarioFile(
                "conf.py",
                _CONF_PY.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.md", _INDEX_MD),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("myparser",),
    )


@pytest.mark.integration
def test_no_index_registers_no_argparse_domain_entries(
    no_index_result: SharedSphinxResult,
) -> None:
    """No ``argparse:*`` cross-reference targets land in objects.inv."""
    inventory = _load_inventory(no_index_result)
    argparse_domains = [
        domain for domain in inventory if domain.startswith("argparse:")
    ]
    assert argparse_domains == []


@pytest.mark.integration
def test_no_index_registers_no_std_cmdoption(
    no_index_result: SharedSphinxResult,
) -> None:
    """No ``std:cmdoption`` entries and an empty std-domain progoptions table."""
    inventory = _load_inventory(no_index_result)
    assert inventory.get("std:cmdoption", {}) == {}

    std_domain = no_index_result.app.env.domains.standard_domain
    assert dict(std_domain.progoptions) == {}


@pytest.mark.integration
def test_no_index_still_renders_the_card(
    no_index_result: SharedSphinxResult,
) -> None:
    """The parser still renders with per-section HTML anchors."""
    index_html = read_output(no_index_result, "index.html")
    assert "Usage" in index_html
    assert 'id="usage"' in index_html
