"""Tests for the ``sphinx-gp-highlighting`` directory tree lexer."""

from __future__ import annotations

import importlib
import typing as t

import pytest
from pygments.token import Comment, Name, Punctuation

from sphinx_gp_highlighting.lexers import DirectoryTreeLexer
from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)


class TreeAliasFixture(t.NamedTuple):
    """Alias case for :class:`DirectoryTreeLexer` registration."""

    test_id: str
    alias: str


_TREE_ALIAS_FIXTURES: list[TreeAliasFixture] = [
    TreeAliasFixture(test_id="short_alias", alias="tree"),
    TreeAliasFixture(test_id="directory_tree_alias", alias="directory-tree"),
    TreeAliasFixture(test_id="dir_tree_alias", alias="dir-tree"),
]


@pytest.mark.parametrize(
    list(TreeAliasFixture._fields),
    _TREE_ALIAS_FIXTURES,
    ids=[case.test_id for case in _TREE_ALIAS_FIXTURES],
)
def test_directory_tree_alias_resolves_to_lexer(test_id: str, alias: str) -> None:
    """Each public tree alias resolves to the package lexer."""
    get_lexer_by_name = t.cast(
        t.Callable[[str], object],
        getattr(importlib.import_module("pygments.lexers"), "get_lexer_by_name"),
    )
    lexer = get_lexer_by_name(alias)
    assert isinstance(lexer, DirectoryTreeLexer), test_id


def test_directory_tree_lexer_tokenizes_connectors_names_and_comments() -> None:
    """Tree output receives structural tokens instead of generic console output."""
    source = (
        "python_module\n"
        "├── tmuxp_plugin_my_plugin_module\n"
        "│   ├── __init__.py\n"
        "│   └── plugin.py\n"
        "└── pyproject.toml  # Python project configuration file\n"
    )

    tokens = list(DirectoryTreeLexer().get_tokens(source))

    assert (Name.Namespace, "python_module") in tokens
    assert (Punctuation, "├──") in tokens
    assert (Punctuation, "│") in tokens
    assert (Punctuation, "└──") in tokens
    assert (Name.Namespace, "tmuxp_plugin_my_plugin_module") in tokens
    assert (Name, "__init__.py") in tokens
    assert (Name, "pyproject.toml") in tokens
    assert (Comment.Single, "# Python project configuration file") in tokens


_CONF_PY = """\
extensions = ["myst_parser", "sphinx_gp_highlighting"]
"""

_INDEX_MD = """\
# Tree block

```tree
python_module
├── tmuxp_plugin_my_plugin_module
│   ├── __init__.py
│   └── plugin.py
└── pyproject.toml  # Python project configuration file
```
"""


@pytest.fixture(scope="module")
def highlighting_tree_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a minimal Sphinx project with a ``tree`` fence."""
    cache_root = tmp_path_factory.mktemp("highlighting-tree")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("conf.py", _CONF_PY),
            ScenarioFile("index.md", _INDEX_MD),
        ),
    )
    return build_shared_sphinx_result(cache_root, scenario)


@pytest.mark.integration
def test_tree_fence_renders_with_tree_highlight_class(
    highlighting_tree_result: SharedSphinxResult,
) -> None:
    """A MyST ``tree`` fence renders through the package lexer."""
    html = read_output(highlighting_tree_result, "index.html")
    assert "highlight-tree" in html
    assert '<span class="p">├──</span>' in html
    assert '<span class="c1"># Python project configuration file</span>' in html
