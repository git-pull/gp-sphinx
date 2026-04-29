"""Sphinx configuration for gp-sphinx documentation."""

from __future__ import annotations

import pathlib
import sys
import typing as t

from pygments.lexer import RegexLexer, bygroups as _bygroups, include
from pygments.token import (
    Comment,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
)
from sphinx.highlighting import lexers

# ``pygments.lexer.bygroups`` ships untyped, which trips
# ``[no-untyped-call]`` under our strict mypy config when the
# function is invoked inside a typed module like this conf.py.
# Aliasing through a ``t.Callable[..., t.Any]`` re-binding keeps the
# call sites readable and satisfies mypy without disabling the rule
# globally. Pattern taken from
# ``~/work/cihai/unihan-etl/docs/conf.py``.
bygroups: t.Callable[..., t.Any] = _bygroups

# Bootstrap: allow importing workspace packages during development
cwd = pathlib.Path(__file__).parent
project_root = cwd.parent
sys.path.insert(0, str(project_root / "packages" / "gp-sphinx" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sphinx-fonts" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sphinx-gp-theme" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sphinx-autodoc-argparse" / "src"))
sys.path.insert(
    0,
    str(project_root / "packages" / "sphinx-autodoc-pytest-fixtures" / "src"),
)
sys.path.insert(0, str(project_root / "packages" / "sphinx-autodoc-docutils" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sphinx-autodoc-sphinx" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sphinx-autodoc-api-style" / "src"))
sys.path.insert(
    0,
    str(project_root / "packages" / "sphinx-ux-badges" / "src"),
)
sys.path.insert(
    0,
    str(project_root / "packages" / "sphinx-autodoc-fastmcp" / "src"),
)
sys.path.insert(
    0,
    str(project_root / "packages" / "sphinx-ux-autodoc-layout" / "src"),
)
sys.path.insert(
    0,
    str(project_root / "packages" / "sphinx-autodoc-typehints-gp" / "src"),
)
sys.path.insert(0, str(cwd / "_ext"))  # docs demo modules

import gp_sphinx  # noqa: E402
from gp_sphinx.config import merge_sphinx_config  # noqa: E402

intersphinx_mapping = {
    "py": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}

conf = merge_sphinx_config(
    project=gp_sphinx.__title__,
    version=gp_sphinx.__version__,
    copyright=gp_sphinx.__copyright__,
    source_repository=f"{gp_sphinx.__github__}/",
    docs_url=gp_sphinx.__docs__,
    source_branch="main",
    extra_extensions=[
        "inline_highlight",
        "package_reference",
        "sab_demo",
        "sab_meta",
        "sphinx_ux_badges",
        "sphinx_autodoc_api_style",
        "sphinx_autodoc_pytest_fixtures",
        "sphinx_autodoc_docutils",
        "sphinx_autodoc_fastmcp",
        "sphinx_autodoc_sphinx",
        "sphinx_autodoc_argparse.exemplar",
        "sphinx_ux_autodoc_layout",
        "gp_sphinx_astro_builder",
    ],
    fastmcp_tool_modules=["fastmcp_demo_tools"],
    fastmcp_area_map={
        "fastmcp_demo_tools": "packages/sphinx-autodoc-fastmcp/examples",
    },
    fastmcp_collector_mode="introspect",
    api_layout_enabled=True,
    api_collapsed_threshold=10,
    pytest_fixture_lint_level="none",
    rediraffe_redirects="redirects.txt",
    intersphinx_mapping=intersphinx_mapping,
    # Enable Vite orchestration: under `sphinx-autobuild`,
    # sphinx-vite-builder spawns `pnpm exec vite build --watch` so
    # contributors editing gp-furo-theme/web/src see fresh CSS/JS on
    # disk without remembering a separate command. No-op for
    # `sphinx-build` (mode resolves to "prod"), so wheel publishes
    # carry no Node runtime requirement.
    vite_orchestration=True,
)
globals().update(conf)


class JustfileLexer(RegexLexer):
    """Pygments lexer for ``justfile`` (https://just.systems/) syntax.

    Pygments has no built-in justfile lexer at the time of writing,
    so docs that show justfile snippets either fall back to plain
    ``text`` (no highlighting) or pick a near-relative like ``make``
    that mistokenises just-specific syntax (``[private]`` recipe
    attributes, ``{{ … }}`` interpolations, ``set`` / ``import``
    keywords). This lexer covers the syntax we actually use in
    gp-sphinx docs:

    - ``# ...`` comments
    - ``[private]`` / ``[no-exit-message]`` / etc. recipe attributes
    - ``set shell := [...]`` / ``import "path"`` / ``mod name`` /
      ``alias x := y`` top-level statements
    - ``var := "value"`` variable assignments
    - ``recipe-name dep1 dep2: prereq`` recipe headers
    - ``{{ expression }}`` interpolations
    - String literals (``"..."``, ``'...'``, ```backticks```)

    Recipe bodies are not parsed deeply — they're treated as Text
    until the next non-indented line. Most justfiles delegate the
    body to a shell, and accurate sub-shell highlighting is more
    work than the docs need.

    Pattern follows the ``CsvLexer`` / ``TsvLexer`` shape in
    ~/work/cihai/unihan-etl/docs/conf.py.
    """

    name = "Justfile"
    aliases: t.ClassVar[list[str]] = ["just", "justfile"]
    filenames: t.ClassVar[list[str]] = ["justfile", "Justfile", "*.just"]
    mimetypes: t.ClassVar[list[str]] = ["text/x-justfile"]

    tokens: t.ClassVar = {
        "root": [
            (r"#.*$", Comment.Single),
            (r"\s+", Text),
            # Recipe attributes: [private], [no-exit-message], [confirm], etc.
            (
                r"^(\[)([a-zA-Z_-]+)((?:\s*\([^)]*\))?)(\])",
                bygroups(
                    Punctuation,
                    Name.Decorator,
                    Text,
                    Punctuation,
                ),
            ),
            # Settings: set shell := [...]
            (
                r"^(set)(\s+)([a-zA-Z_-]+)",
                bygroups(Keyword.Reserved, Text, Name.Variable),
                "assignment",
            ),
            # Module / alias / export / import / unexport at line start.
            (
                r"^(import|mod|alias|export|unexport)\b",
                Keyword.Reserved,
            ),
            # Variable assignment at line start.
            (
                r"^([a-zA-Z_][a-zA-Z0-9_-]*)(\s*)(:=)",
                bygroups(Name.Variable, Text, Operator),
                "assignment",
            ),
            # Recipe header: name [params]: [prereqs]
            (
                r"^([a-zA-Z_][a-zA-Z0-9_-]*)((?:\s+[a-zA-Z0-9_+*=\"'-]+)*)(\s*:)",
                bygroups(Name.Function, Text, Punctuation),
                "recipe-body",
            ),
            include("strings"),
        ],
        "assignment": [
            (r"\n", Text, "#pop"),
            include("strings"),
            (r"\{\{", String.Interpol, "interpol"),
            (r"[+\-*/%]", Operator),
            (r"[a-zA-Z_][a-zA-Z0-9_-]*", Name),
            (r"[0-9]+", Number),
            (r"[\[\](),]", Punctuation),
            (r"\s+", Text),
            (r":=", Operator),
            (r".", Text),
        ],
        "recipe-body": [
            # End of body: a line that doesn't start with whitespace.
            (r"\n(?=\S)", Text, "#pop"),
            (r"\n", Text),
            (r"#.*$", Comment.Single),
            (r"\{\{", String.Interpol, "interpol"),
            include("strings"),
            (r".", Text),
        ],
        "interpol": [
            (r"\}\}", String.Interpol, "#pop"),
            (r"[a-zA-Z_][a-zA-Z0-9_]*", Name.Variable),
            (r"\(", Punctuation),
            (r"\)", Punctuation),
            include("strings"),
            (r"\s+", Text),
            (r".", Text),
        ],
        "strings": [
            (r'"[^"\n]*"', String.Double),
            (r"'[^'\n]*'", String.Single),
            (r"`[^`\n]*`", String.Backtick),
        ],
    }


lexers["just"] = JustfileLexer()
