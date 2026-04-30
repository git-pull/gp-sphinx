"""Tests for the gp-sphinx-light Pygments style and Furo's emitted CSS.

Covers three layers:

1. The custom :class:`GpSphinxLightStyle` is discoverable via
   :func:`pygments.styles.get_style_by_name` and exposes the expected
   token-to-color mappings (CodeMirror-derived light palette).
2. The :class:`pygments.formatters.HtmlFormatter` output for the style is
   stable (snapshot assertion).
3. Sphinx builds with ``sphinx-gp-theme`` produce a ``_static/pygments.css``
   that contains the light palette in the unscoped block AND a
   ``body[data-theme="dark"]`` block with the paired monokai dark style.
"""

from __future__ import annotations

import textwrap
import typing as t

import pytest
from pygments import formatters, token
from pygments.styles import get_style_by_name

from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

# ---------------------------------------------------------------------------
# Pure unit tests — style class registration & token mapping
# ---------------------------------------------------------------------------


def test_gp_sphinx_light_resolved_by_name() -> None:
    """The style is resolvable by its registered name."""
    style = get_style_by_name("gp-sphinx-light")
    assert style.__name__ == "GpSphinxLightStyle"
    assert style.background_color == "#f8fafc"


def test_gp_sphinx_light_line_number_palette() -> None:
    """Line-number gutter uses the slate-100 / slate-500 palette."""
    style = get_style_by_name("gp-sphinx-light")
    assert style.line_number_color == "#64748b"
    assert style.line_number_background_color == "#f1f5f9"


class TokenColorCase(t.NamedTuple):
    """Expected color/style snippet for a Pygments token."""

    test_id: str
    token: token._TokenType
    expected_substring: str


_TOKEN_COLOR_FIXTURES: list[TokenColorCase] = [
    TokenColorCase(
        test_id="comment-italic-slate",
        token=token.Comment,
        expected_substring="italic #64748b",
    ),
    TokenColorCase(
        test_id="keyword-bold-purple",
        token=token.Keyword,
        expected_substring="bold #7c3aed",
    ),
    TokenColorCase(
        test_id="operator-word-bold-purple",
        token=token.Operator.Word,
        expected_substring="bold #7c3aed",
    ),
    TokenColorCase(
        test_id="string-yellow",
        token=token.String,
        expected_substring="#ca8a04",
    ),
    TokenColorCase(
        test_id="number-blue",
        token=token.Number,
        expected_substring="#3b82f6",
    ),
    TokenColorCase(
        test_id="builtin-orange",
        token=token.Name.Builtin,
        expected_substring="#ea580c",
    ),
    TokenColorCase(
        test_id="tag-red",
        token=token.Name.Tag,
        expected_substring="#dc2626",
    ),
    TokenColorCase(
        test_id="attribute-purple-light",
        token=token.Name.Attribute,
        expected_substring="#a855f7",
    ),
    TokenColorCase(
        test_id="generic-inserted-green",
        token=token.Generic.Inserted,
        expected_substring="#16a34a",
    ),
    TokenColorCase(
        test_id="generic-deleted-red",
        token=token.Generic.Deleted,
        expected_substring="#dc2626",
    ),
]


@pytest.mark.parametrize(
    list(TokenColorCase._fields),
    _TOKEN_COLOR_FIXTURES,
    ids=[case.test_id for case in _TOKEN_COLOR_FIXTURES],
)
def test_gp_sphinx_light_token_palette(
    test_id: str,
    token: token._TokenType,
    expected_substring: str,
) -> None:
    """Each documented token maps to the expected CodeMirror-derived value."""
    style = get_style_by_name("gp-sphinx-light")
    assert expected_substring in style.styles[token], (
        f"{test_id}: {token} -> {style.styles[token]!r} missing {expected_substring!r}"
    )


# ---------------------------------------------------------------------------
# Snapshot — HtmlFormatter style defs
# ---------------------------------------------------------------------------


def test_gp_sphinx_light_html_style_defs(
    snapshot_html_fragment: t.Callable[..., None],
) -> None:
    """The HtmlFormatter CSS for the style is stable across runs.

    Locks the full per-token CSS surface so accidental drift in any color or
    weight surfaces in CI rather than only at visual review time.
    """
    formatter = formatters.HtmlFormatter(style="gp-sphinx-light")
    css: str = formatter.get_style_defs(".highlight")  # type: ignore[no-untyped-call]
    snapshot_html_fragment(css)


# ---------------------------------------------------------------------------
# Sphinx integration — light + dark scopes in built pygments.css
# ---------------------------------------------------------------------------


_INTEGRATION_CONF_PY = textwrap.dedent(
    """\
    project = "gp-sphinx-pygments-test"
    extensions = ["myst_parser"]
    html_theme = "sphinx-gp-theme"
    pygments_style = "gp-sphinx-light"
    pygments_dark_style = "monokai"
    master_doc = "index"
    source_suffix = {".md": "markdown"}
    exclude_patterns = []
    """
)

_INTEGRATION_INDEX_MD = textwrap.dedent(
    """\
    # Pygments smoke test

    ```python
    def greet(name: str) -> str:
        return f"hello {name}"
    ```
    """
)


@pytest.fixture(scope="module")
def gp_sphinx_pygments_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a tiny Sphinx project using sphinx-gp-theme + paired styles."""
    cache_root = tmp_path_factory.mktemp("gp-sphinx-pygments")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("conf.py", _INTEGRATION_CONF_PY),
            ScenarioFile("index.md", _INTEGRATION_INDEX_MD),
        ),
    )
    return build_shared_sphinx_result(cache_root, scenario)


@pytest.mark.integration
def test_built_pygments_css_contains_light_palette(
    gp_sphinx_pygments_result: SharedSphinxResult,
) -> None:
    """The unscoped ``.highlight`` block carries the CodeMirror light palette."""
    css = read_output(gp_sphinx_pygments_result, "_static/pygments.css").lower()
    assert ".highlight .k {" in css
    assert "#7c3aed" in css
    assert "#ca8a04" in css
    assert "#3b82f6" in css
    assert "background: #f8fafc" in css


@pytest.mark.integration
def test_built_pygments_css_contains_dark_scope(
    gp_sphinx_pygments_result: SharedSphinxResult,
) -> None:
    """Furo emits a ``body[data-theme="dark"]`` block for the paired dark style."""
    css = read_output(gp_sphinx_pygments_result, "_static/pygments.css").lower()
    assert 'body[data-theme="dark"] .highlight' in css
    # Monokai-specific colours that should appear only inside the dark scope.
    assert "#272822" in css  # monokai background
    assert "#66d9ef" in css  # monokai keyword cyan
