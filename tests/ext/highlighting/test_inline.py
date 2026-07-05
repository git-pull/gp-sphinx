"""Tests for ``sphinx-gp-highlighting`` inline literal helpers."""

from __future__ import annotations

import textwrap
import typing as t

import pytest

from sphinx_gp_highlighting.inline import (
    InlineLiteralKind,
    build_highlighted_literal,
    classify_inline_literal,
)
from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)


class InlineClassificationFixture(t.NamedTuple):
    """Case for safe inline literal classification."""

    test_id: str
    text: str
    commands: tuple[str, ...]
    expected: InlineLiteralKind | None


_INLINE_CLASSIFICATION_FIXTURES: list[InlineClassificationFixture] = [
    InlineClassificationFixture(
        test_id="configured_command",
        text="tmuxp freeze my-session",
        commands=("tmuxp",),
        expected="command",
    ),
    InlineClassificationFixture(
        test_id="shell_session",
        text="$ tmuxp freeze my-session",
        commands=(),
        expected="shell-session",
    ),
    InlineClassificationFixture(
        test_id="home_dir",
        text="~/.config/tmuxp/",
        commands=(),
        expected="dir",
    ),
    InlineClassificationFixture(
        test_id="home_file",
        text="~/.config/tmuxp/config.yaml",
        commands=(),
        expected="path",
    ),
    InlineClassificationFixture(
        test_id="relative_dir",
        text="./docs/",
        commands=(),
        expected="dir",
    ),
    InlineClassificationFixture(
        test_id="wsl_absolute_path",
        text="/mnt/c/Users/example/AppData/Roaming",
        commands=(),
        expected="path",
    ),
    InlineClassificationFixture(
        test_id="mime_type",
        text="application/json",
        commands=(),
        expected=None,
    ),
    InlineClassificationFixture(
        test_id="mcp_method",
        text="resources/read",
        commands=(),
        expected=None,
    ),
    InlineClassificationFixture(
        test_id="cli_option_pair",
        text="-0/--print0",
        commands=(),
        expected=None,
    ),
    InlineClassificationFixture(
        test_id="http_api_endpoint",
        text="/api/pull",
        commands=(),
        expected=None,
    ),
    InlineClassificationFixture(
        test_id="plain_python_name",
        text="module_name",
        commands=("tmuxp",),
        expected=None,
    ),
]


@pytest.mark.parametrize(
    list(InlineClassificationFixture._fields),
    _INLINE_CLASSIFICATION_FIXTURES,
    ids=[case.test_id for case in _INLINE_CLASSIFICATION_FIXTURES],
)
def test_classify_inline_literal_safe_shapes(
    test_id: str,
    text: str,
    commands: tuple[str, ...],
    expected: InlineLiteralKind | None,
) -> None:
    """Only safe command/path shapes are classified."""
    assert classify_inline_literal(text, commands=commands) == expected, test_id


def test_build_highlighted_literal_sets_language_for_commands() -> None:
    """Command literals use Sphinx's inline Pygments path."""
    node = build_highlighted_literal("tmuxp freeze my-session", "command")
    assert "gp-sphinx-highlighting-inline" in node["classes"]
    assert "gp-sphinx-highlighting-inline--kind-command" in node["classes"]
    assert "code" in node["classes"]
    assert node["language"] == "bash"


def test_build_highlighted_literal_leaves_paths_unlanguaged() -> None:
    """Path literals get semantic classes without pretending to be code."""
    node = build_highlighted_literal("~/.config/tmuxp/", "dir")
    assert "gp-sphinx-highlighting-inline--kind-dir" in node["classes"]
    assert "language" not in node


_CONF_PY = textwrap.dedent(
    """\
    extensions = ["myst_parser", "sphinx_gp_highlighting"]
    gp_highlighting_inline_literals = "safe"
    gp_highlighting_inline_commands = ["tmuxp"]
    """
)

_INDEX_MD = textwrap.dedent(
    """\
    # Inline highlighting

    Auto command: `tmuxp freeze my-session`

    Auto dir: `~/.config/tmuxp/`

    Plain literal: `module_name`

    Explicit command: {cmd}`tmuxp freeze my-session`

    Explicit path: {path}`~/.config/tmuxp/config.yaml`

    Explicit dir: {dir}`~/.config/tmuxp/`
    """
)


@pytest.fixture(scope="module")
def highlighting_inline_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a minimal Sphinx project with inline highlighting enabled."""
    cache_root = tmp_path_factory.mktemp("highlighting-inline")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("conf.py", _CONF_PY),
            ScenarioFile("index.md", _INDEX_MD),
        ),
    )
    return build_shared_sphinx_result(cache_root, scenario)


@pytest.mark.integration
def test_inline_roles_and_safe_literals_render_classes(
    highlighting_inline_result: SharedSphinxResult,
) -> None:
    """Explicit roles and safe backtick literals render package classes."""
    html = read_output(highlighting_inline_result, "index.html")

    assert "gp-sphinx-highlighting-inline--kind-command" in html
    assert "gp-sphinx-highlighting-inline--kind-path" in html
    assert "gp-sphinx-highlighting-inline--kind-dir" in html
    assert "highlight-bash" in html
    assert "module_name</span>" in html
    assert "sphinx_gp_highlighting.css" in html
