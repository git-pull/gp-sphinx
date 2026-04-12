"""Unit and integration tests for ArgparseDomain.

Unit tests construct ArgparseDomain against a lightweight stub env,
exercise the note / clear / merge / resolve lifecycle, and verify the
two auto-generated indices.  One integration test builds a synthetic
Sphinx project end-to-end and asserts that the domain is populated
after a real build and that ``:argparse:*`` cross-references resolve.
"""

from __future__ import annotations

import io
import pathlib
import re
import sys
import textwrap
import typing as t

import pytest
from docutils import nodes

from sphinx_autodoc_argparse.domain import (
    OBJECT_TYPES,
    OPTION,
    POSITIONAL,
    PROGRAM,
    SUBCOMMAND,
    ArgparseDomain,
    ArgparseOptionsIndex,
    ArgparseProgramsIndex,
)

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx


# ---------------------------------------------------------------------------
# Unit tests — no Sphinx build
# ---------------------------------------------------------------------------


class _StubEnv:
    """Minimal stand-in for ``BuildEnvironment`` — just ``domaindata``."""

    def __init__(self) -> None:
        self.domaindata: dict[str, dict[str, t.Any]] = {}


def _make_domain() -> ArgparseDomain:
    """Build an ArgparseDomain bound to a fresh stub environment."""
    return ArgparseDomain(t.cast("t.Any", _StubEnv()))


def test_object_types_constants_match_domain() -> None:
    """Module-level PROGRAM/OPTION/SUBCOMMAND/POSITIONAL names match domain keys."""
    assert set(OBJECT_TYPES) == {PROGRAM, OPTION, SUBCOMMAND, POSITIONAL}
    assert set(ArgparseDomain.object_types) == set(OBJECT_TYPES)


def test_initial_data_contains_four_empty_tables() -> None:
    """Fresh domain starts with four empty object tables."""
    domain = _make_domain()
    assert domain.programs == {}
    assert domain.options == {}
    assert domain.subcommands == {}
    assert domain.positionals == {}


def test_note_program_records_docname_and_anchor() -> None:
    """note_program stores (docname, anchor) under the program name."""
    domain = _make_domain()
    domain.note_program("myapp", "cli", "argparse-myapp")
    assert domain.programs == {"myapp": ("cli", "argparse-myapp")}


def test_note_option_keyed_by_program_name_tuple() -> None:
    """note_option uses (program, name) composite keys."""
    domain = _make_domain()
    domain.note_option("myapp", "--verbose", "cli", "verbose")
    domain.note_option("myapp sync", "--force", "cli", "sync-force")
    assert domain.options == {
        ("myapp", "--verbose"): ("cli", "verbose"),
        ("myapp sync", "--force"): ("cli", "sync-force"),
    }


def test_note_subcommand_and_positional_store_separately() -> None:
    """Subcommands and positionals use their own dicts."""
    domain = _make_domain()
    domain.note_subcommand("myapp", "sync", "cli", "argparse-myapp-sync")
    domain.note_positional("myapp", "FILE", "cli", "file")
    assert domain.subcommands == {("myapp", "sync"): ("cli", "argparse-myapp-sync")}
    assert domain.positionals == {("myapp", "FILE"): ("cli", "file")}


def test_clear_doc_removes_only_matching_docname() -> None:
    """clear_doc drops entries from *docname* and keeps the rest."""
    domain = _make_domain()
    domain.note_program("myapp", "cli", "argparse-myapp")
    domain.note_program("other", "other-page", "argparse-other")
    domain.note_option("myapp", "--verbose", "cli", "verbose")
    domain.note_option("other", "--debug", "other-page", "debug")

    domain.clear_doc("cli")

    assert domain.programs == {"other": ("other-page", "argparse-other")}
    assert domain.options == {("other", "--debug"): ("other-page", "debug")}


def test_merge_domaindata_merges_entries_within_docnames() -> None:
    """Parallel-worker merge retains entries for docnames in the active set."""
    domain = _make_domain()
    other = {
        "programs": {"sibling": ("pageB", "argparse-sibling")},
        "options": {("sibling", "--flag"): ("pageB", "flag")},
        "subcommands": {},
        "positionals": {},
    }
    domain.merge_domaindata({"pageB"}, other)
    assert domain.programs == {"sibling": ("pageB", "argparse-sibling")}
    assert domain.options == {("sibling", "--flag"): ("pageB", "flag")}


def test_merge_domaindata_ignores_entries_outside_docnames() -> None:
    """Entries whose docname is NOT in *docnames* are dropped on merge."""
    domain = _make_domain()
    other = {
        "programs": {"sibling": ("pageC", "argparse-sibling")},
        "options": {},
        "subcommands": {},
        "positionals": {},
    }
    domain.merge_domaindata({"pageB"}, other)
    assert domain.programs == {}


def test_get_objects_yields_every_registered_item() -> None:
    """get_objects iterates programs, options, subcommands, and positionals."""
    domain = _make_domain()
    domain.note_program("myapp", "cli", "argparse-myapp")
    domain.note_option("myapp", "--verbose", "cli", "verbose")
    domain.note_subcommand("myapp", "sync", "cli", "argparse-myapp-sync")
    domain.note_positional("myapp", "FILE", "cli", "file")

    rows = list(domain.get_objects())
    types = {row[2] for row in rows}
    assert types == {PROGRAM, OPTION, SUBCOMMAND, POSITIONAL}
    assert len(rows) == 4


# ---------------------------------------------------------------------------
# Lookup + xref resolution
# ---------------------------------------------------------------------------


def test_lookup_program_exact_match() -> None:
    """Program lookup matches on exact name."""
    domain = _make_domain()
    domain.note_program("myapp", "cli", "argparse-myapp")
    assert domain._lookup(PROGRAM, "myapp") == ("cli", "argparse-myapp")
    assert domain._lookup(PROGRAM, "nope") is None


def test_lookup_option_accepts_whitespace_joined_target() -> None:
    """Option lookup splits "program name" targets into tuple keys."""
    domain = _make_domain()
    domain.note_option("myapp sync", "--force", "cli", "sync-force")
    assert domain._lookup(OPTION, "myapp sync --force") == ("cli", "sync-force")


def test_lookup_option_falls_back_to_bare_name() -> None:
    """Bare option name resolves if there's a single matching registration."""
    domain = _make_domain()
    domain.note_option("myapp", "--verbose", "cli", "verbose")
    assert domain._lookup(OPTION, "--verbose") == ("cli", "verbose")


def test_lookup_unknown_objtype_returns_none() -> None:
    """Unknown objtype strings return None without raising."""
    domain = _make_domain()
    assert domain._lookup("bogus", "anything") is None


# ---------------------------------------------------------------------------
# Index generation
# ---------------------------------------------------------------------------


def test_programs_index_generates_alphabetised_entries() -> None:
    """ArgparseProgramsIndex groups by first letter and sorts names."""
    domain = _make_domain()
    domain.note_program("beta", "pageB", "argparse-beta")
    domain.note_program("alpha", "pageA", "argparse-alpha")

    index = ArgparseProgramsIndex(domain)
    content, collapse = index.generate()

    assert collapse is False
    letters = [letter for letter, _entries in content]
    assert letters == ["a", "b"]
    # Within "a", only "alpha"
    assert len(content[0][1]) == 1
    assert content[0][1][0].name == "alpha"
    assert content[0][1][0].docname == "pageA"


def test_options_index_groups_by_program() -> None:
    """ArgparseOptionsIndex headings are program names; entries are options."""
    domain = _make_domain()
    domain.note_option("myapp", "--verbose", "cli", "verbose")
    domain.note_option("myapp", "-v", "cli", "v")
    domain.note_option("myapp sync", "--force", "cli", "sync-force")

    index = ArgparseOptionsIndex(domain)
    content, collapse = index.generate()

    assert collapse is True
    headings = [heading for heading, _entries in content]
    assert headings == ["myapp", "myapp sync"]


def test_programs_index_filters_by_docnames() -> None:
    """When docnames is given, only matching entries are yielded."""
    domain = _make_domain()
    domain.note_program("a_prog", "pageA", "a")
    domain.note_program("b_prog", "pageB", "b")

    index = ArgparseProgramsIndex(domain)
    content, _ = index.generate(docnames={"pageA"})
    all_names = [entry.name for _letter, entries in content for entry in entries]
    assert all_names == ["a_prog"]


# ---------------------------------------------------------------------------
# Integration test — full Sphinx build through the argparse directive
# ---------------------------------------------------------------------------


_PARSER_MOD = textwrap.dedent(
    """\
    from __future__ import annotations

    import argparse


    def create_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="demo")
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
       :module: demoparser
       :func: create_parser
       :prog: demo
    ```
    """,
)


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class _Result(t.NamedTuple):
    app: Sphinx
    warnings: str
    outdir: pathlib.Path


def _purge_demoparser() -> None:
    for key in list(sys.modules):
        if key == "demoparser":
            del sys.modules[key]


@pytest.fixture(scope="module")
def domain_result(tmp_path_factory: pytest.TempPathFactory) -> _Result:
    """Build a synthetic project exercising the argparse directive."""
    from sphinx.application import Sphinx

    tmp_path = tmp_path_factory.mktemp("argparse-domain-unit-integration")
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    doctreedir = tmp_path / ".doctrees"
    srcdir.mkdir()
    outdir.mkdir()
    doctreedir.mkdir()

    (srcdir / "demoparser.py").write_text(_PARSER_MOD, encoding="utf-8")
    (srcdir / "conf.py").write_text(
        _CONF_PY.format(srcdir=str(srcdir)),
        encoding="utf-8",
    )
    (srcdir / "index.md").write_text(_INDEX_MD, encoding="utf-8")

    status_buf = io.StringIO()
    warning_buf = io.StringIO()

    _purge_demoparser()

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

    warnings = _ANSI_RE.sub("", warning_buf.getvalue())
    return _Result(app=app, warnings=warnings, outdir=outdir)


@pytest.mark.integration
def test_domain_populated_after_real_build(domain_result: _Result) -> None:
    """After a real build, the argparse domain holds program + option entries."""
    domain = domain_result.app.env.domains["argparse"]
    programs = domain.programs  # type: ignore[attr-defined]
    options = domain.options  # type: ignore[attr-defined]
    subcommands = domain.subcommands  # type: ignore[attr-defined]
    positionals = domain.positionals  # type: ignore[attr-defined]

    assert "demo" in programs
    assert "demo sync" in programs
    assert ("demo", "--verbose") in options
    assert ("demo", "-v") in options
    assert ("demo sync", "--force") in options
    assert ("demo", "sync") in subcommands
    assert ("demo", "filename") in positionals


@pytest.mark.integration
def test_domain_resolves_xref_after_real_build(domain_result: _Result) -> None:
    """resolve_xref returns a reference node for a registered option target."""
    env = domain_result.app.env
    domain = env.domains["argparse"]

    from sphinx.addnodes import pending_xref

    refnode = domain.resolve_xref(
        env,
        "index",
        domain_result.app.builder,
        OPTION,
        "demo --verbose",
        pending_xref(),
        nodes.literal(),
    )
    assert refnode is not None
    assert refnode.tagname == "reference"
