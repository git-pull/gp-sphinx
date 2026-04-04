"""Tests for gp_sphinx.myst_lexer."""

from __future__ import annotations

import typing as t

import pytest

from gp_sphinx.myst_lexer import MystLexer, tokenize_myst

# --- Helper ---


def get_tokens(text: str) -> list[tuple[str, str]]:
    """Return (token_type_str, value) tuples for *text* via MystLexer."""
    lexer = MystLexer()
    return [(str(tok), val) for tok, val in lexer.get_tokens(text)]


# ---------------------------------------------------------------------------
# Fence markers: {eval-rst} opening/closing emitted as String.Backtick
# ---------------------------------------------------------------------------

_BACKTICK = "Token.Literal.String.Backtick"


class FenceFixture(t.NamedTuple):
    test_id: str
    input_text: str
    expected_contains: list[tuple[str, str]]


FENCE_FIXTURES: list[FenceFixture] = [
    FenceFixture(
        test_id="fence_opening_is_backtick",
        input_text="```{eval-rst}\nHello\n```\n",
        expected_contains=[(_BACKTICK, "```{eval-rst}")],
    ),
    FenceFixture(
        test_id="fence_with_info_string",
        input_text="```{eval-rst} some-arg\nHello\n```\n",
        expected_contains=[(_BACKTICK, "```{eval-rst} some-arg")],
    ),
    FenceFixture(
        test_id="fence_closing_is_backtick",
        input_text="```{eval-rst}\nHello\n```\n",
        expected_contains=[(_BACKTICK, "```\n")],
    ),
]


@pytest.mark.parametrize(
    list(FenceFixture._fields),
    FENCE_FIXTURES,
    ids=[f.test_id for f in FENCE_FIXTURES],
)
def test_fence_markers(
    test_id: str,
    input_text: str,
    expected_contains: list[tuple[str, str]],
) -> None:
    tokens = get_tokens(input_text)
    for tok, val in expected_contains:
        assert (tok, val) in tokens, (
            f"Expected ({tok!r}, {val!r}) in tokens for test_id={test_id!r}\n"
            f"Got: {tokens}"
        )


# ---------------------------------------------------------------------------
# Empty block: two String.Backtick tokens (opening + closing)
# ---------------------------------------------------------------------------


def test_empty_eval_rst_block() -> None:
    tokens = get_tokens("```{eval-rst}\n```\n")
    backtick_tokens = [val for tok, val in tokens if tok == _BACKTICK]
    assert len(backtick_tokens) >= 2, (
        f"Expected at least 2 String.Backtick tokens, got: {backtick_tokens}"
    )


# ---------------------------------------------------------------------------
# Regression: plain Markdown and standard fenced blocks still work
# ---------------------------------------------------------------------------


class RegressionFixture(t.NamedTuple):
    test_id: str
    input_text: str
    expected_value_present: str


REGRESSION_FIXTURES: list[RegressionFixture] = [
    RegressionFixture(
        test_id="plain_text_no_regression",
        input_text="Hello world\n",
        expected_value_present="Hello",
    ),
    RegressionFixture(
        test_id="standard_python_fence_regression",
        input_text="```python\nimport this\n```\n",
        expected_value_present="import",
    ),
]


@pytest.mark.parametrize(
    list(RegressionFixture._fields),
    REGRESSION_FIXTURES,
    ids=[f.test_id for f in REGRESSION_FIXTURES],
)
def test_no_regression(
    test_id: str,
    input_text: str,
    expected_value_present: str,
) -> None:
    tokens = get_tokens(input_text)
    values = [val for _, val in tokens]
    assert any(expected_value_present in v for v in values), (
        f"Expected {expected_value_present!r} in some token value for "
        f"test_id={test_id!r}\nValues: {values}"
    )


def test_standard_python_fence_has_keyword() -> None:
    """Standard ```python fence produces Python keyword tokens."""
    tokens = get_tokens("```python\nimport this\n```\n")
    token_types = [tok for tok, _ in tokens]
    assert "Token.Keyword.Namespace" in token_types, (
        f"Expected Python keyword token, got types: {set(token_types)}"
    )


# ---------------------------------------------------------------------------
# 3-level nesting: {eval-rst} -> .. code-block:: python -> Python tokens
# ---------------------------------------------------------------------------

_PY_IMPORT_KEYWORD = "Token.Keyword.Namespace"


class NestedHighlightFixture(t.NamedTuple):
    test_id: str
    input_text: str
    expect_python_tokens: bool


NESTED_HIGHLIGHT_FIXTURES: list[NestedHighlightFixture] = [
    NestedHighlightFixture(
        test_id="python_with_trailing_blank",
        # Trailing blank line before ``` is required by RstLexer._handle_sourcecode
        input_text=("```{eval-rst}\n.. code-block:: python\n\n   import this\n\n```\n"),
        expect_python_tokens=True,
    ),
    NestedHighlightFixture(
        test_id="python_without_trailing_blank_no_highlighting",
        # No trailing blank — RstLexer's regex doesn't match; documents limitation
        input_text=("```{eval-rst}\n.. code-block:: python\n\n   import this\n```\n"),
        expect_python_tokens=False,
    ),
]


@pytest.mark.parametrize(
    list(NestedHighlightFixture._fields),
    NESTED_HIGHLIGHT_FIXTURES,
    ids=[f.test_id for f in NESTED_HIGHLIGHT_FIXTURES],
)
def test_nested_highlight(
    test_id: str,
    input_text: str,
    expect_python_tokens: bool,
) -> None:
    tokens = get_tokens(input_text)
    token_types = [tok for tok, _ in tokens]
    has_python = _PY_IMPORT_KEYWORD in token_types
    assert has_python == expect_python_tokens, (
        f"test_id={test_id!r}: expected Python tokens={expect_python_tokens}, "
        f"got={has_python}\nToken types: {sorted(set(token_types))}"
    )


# ---------------------------------------------------------------------------
# Multiple {eval-rst} blocks in one file
# ---------------------------------------------------------------------------


def test_multiple_eval_rst_blocks() -> None:
    src = (
        "```{eval-rst}\nFirst block\n```\n"
        "\n"
        "Some text in between.\n"
        "\n"
        "```{eval-rst}\nSecond block\n```\n"
    )
    tokens = get_tokens(src)
    backtick_tokens = [val for tok, val in tokens if tok == _BACKTICK]
    # Two opening fences + two closing fences = at least 4
    assert len(backtick_tokens) >= 4, (
        f"Expected at least 4 String.Backtick tokens (2 open + 2 close), "
        f"got {len(backtick_tokens)}: {backtick_tokens}"
    )


# ---------------------------------------------------------------------------
# {eval-rst} block at end of file without trailing newline
# ---------------------------------------------------------------------------


def test_eval_rst_block_at_eof() -> None:
    src = "```{eval-rst}\nHello RST\n```"  # no trailing newline
    tokens = get_tokens(src)
    backtick_tokens = [val for tok, val in tokens if tok == _BACKTICK]
    assert "```{eval-rst}" in backtick_tokens, (
        f"Expected opening fence token at EOF, got: {backtick_tokens}"
    )


# ---------------------------------------------------------------------------
# tokenize_myst helper function
# ---------------------------------------------------------------------------


def test_tokenize_myst_helper() -> None:
    tokens = tokenize_myst("Hello world")
    assert any("Hello" in v for _, v in tokens)


def test_tokenize_myst_returns_backtick_for_eval_rst() -> None:
    tokens = tokenize_myst("```{eval-rst}\nHello RST\n```\n")
    assert (_BACKTICK, "```{eval-rst}") in tokens
