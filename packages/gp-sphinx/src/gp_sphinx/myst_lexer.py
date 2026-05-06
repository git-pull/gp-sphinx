"""Pygments lexer for MyST Markdown source files.

Provides :class:`MystLexer`, a custom Pygments lexer that adds
``{eval-rst}`` fenced block support on top of :class:`MarkdownLexer`.

This module is for highlighting MyST **source files** shown as source
text (e.g. via ``literalinclude`` or docs-of-docs pages). It is NOT
needed for normal Sphinx builds, where MyST is parsed to docutils nodes
before Pygments runs.

Three distinct contexts exist for highlighting MyST content:

- **Sphinx HTML build output**: Already works. MyST parses ``{eval-rst}``
  to docutils nodes before Pygments sees anything. No lexer needed.
- **MyST source shown as source text**: The real gap. This module
  provides the :class:`MystLexer` that fills it.
- **Editors / GitHub UI**: A Pygments lexer cannot help here. That
  requires a tree-sitter or TextMate grammar.

Examples
--------
>>> from gp_sphinx.myst_lexer import tokenize_myst
>>> tokens = tokenize_myst("Hello world")
>>> any("Hello" in v for _, v in tokens)
True
"""

from __future__ import annotations

import typing as t

from pygments.lexers.markup import MarkdownLexer, RstLexer
from pygments.token import Name, String, Text, Whitespace

if t.TYPE_CHECKING:
    import re

    from pygments.token import _TokenType


class MystLexer(MarkdownLexer):
    """Markdown lexer with MyST ``{eval-rst}`` fenced block support.

    For highlighting MyST **source files** shown as source text
    (``literalinclude``, docs-of-docs). NOT needed for normal Sphinx
    builds, where MyST is parsed to docutils nodes before Pygments runs.

    Only ``{eval-rst}`` fenced blocks are handled specially; all other
    Markdown syntax is delegated unchanged to :class:`MarkdownLexer`.

    Token *types* compose correctly through all three levels
    (MyST -> RST -> Python). Token *offsets* are correct at levels 1-2;
    innermost (Python) offsets inherit the upstream ``RstLexer``
    limitation shared with ``MarkdownLexer``'s acknowledged offset
    ``FIXME`` inside ``_handle_codeblock``.

    Examples
    --------
    >>> lexer = MystLexer()
    >>> tokens = [(str(tok), v) for tok, v in lexer.get_tokens("Hello")]
    >>> any(v == "Hello" for _, v in tokens)
    True

    Triple-colon fences (MyST ``colon_fence`` extension) tokenize the
    opening, option keys, and closing markers so source samples
    documenting MyST directives render with proper highlighting:

    >>> tokens = tokenize_myst(":::{note}\\nhi\\n:::\\n")
    >>> any(":::{note}" == v for _, v in tokens)
    True
    """  # noqa: D301 - backslashes are in doctest code, not escape sequences

    name = "MyST Markdown"
    aliases: t.ClassVar[list[str]] = ["myst", "myst-md"]
    filenames: t.ClassVar[list[str]] = ["*.myst.md"]

    def _handle_eval_rst(
        self,
        match: re.Match[str],
    ) -> t.Iterator[tuple[int, _TokenType, str]]:
        """Lex a ``{eval-rst}`` fenced block by delegating body to RstLexer.

        Emits the opening fence as ``String.Backtick``, delegates the
        body to ``RstLexer(handlecodeblocks=True)`` (enabling 3-level
        nesting: MyST fence → RST directive → inner language), then
        emits the closing fence as ``String.Backtick``.

        Parameters
        ----------
        match : re.Match[str]
            Regex match with named groups ``opening``, ``newline``,
            ``body``, and ``closing``.

        Yields
        ------
        tuple[int, _TokenType, str]
            ``(offset, token_type, value)`` triples whose offsets are
            relative to the start of the full document, suitable for
            ``get_tokens_unprocessed``.

        Notes
        -----
        ``RstLexer._handle_sourcecode`` requires at least one line of
        code content followed by a trailing blank line to recognise a
        ``.. code-block::`` directive. Single-line bodies without a
        trailing blank line will not trigger inner language highlighting.

        Token *types* are correct at all three levels. Token *offsets*
        for the innermost (e.g. Python) tokens are relative to the
        stripped code content rather than the full document — an
        upstream limitation in ``do_insertions`` shared with
        ``MarkdownLexer._handle_codeblock``.

        Examples
        --------
        >>> tokens = tokenize_myst("```{eval-rst}\\nHello RST\\n```\\n")
        >>> any("Backtick" in tok for tok, _ in tokens)
        True
        """  # noqa: D301 - backslashes are in doctest code, not escape sequences
        yield match.start("opening"), String.Backtick, match.group("opening")
        yield match.start("newline"), Whitespace, match.group("newline")

        rst_body = match.group("body")
        body_offset = match.start("body")
        rst_lexer = RstLexer(handlecodeblocks=True, stripnl=False)
        for index, token, value in rst_lexer.get_tokens_unprocessed(rst_body):
            # index is relative to rst_body; add body_offset to produce
            # the document-relative position. Innermost (Python) offsets
            # inherit an upstream RstLexer limitation — do_insertions()
            # yields offsets relative to the stripped code content.
            yield body_offset + index, token, value

        yield match.start("closing"), String.Backtick, match.group("closing")

    def _handle_colon_fence(
        self,
        match: re.Match[str],
    ) -> t.Iterator[tuple[int, _TokenType, str]]:
        """Lex a ``:::{<directive>}`` colon-fenced block (MyST ``colon_fence``).

        Emits the opening ``:::{name}`` line and the closing ``:::`` line
        as ``String.Backtick`` (matching how :meth:`_handle_eval_rst`
        renders fence boundaries). Within the body, lines matching the
        ``:<key>: <value>`` MyST option syntax tokenize the key as
        ``Name.Tag`` (RST-style option-list convention) and the value as
        ``Text``; remaining body content is ``Text``.

        Parameters
        ----------
        match : re.Match[str]
            Regex match with named groups ``opening``, ``newline``,
            ``body``, and ``closing``.

        Yields
        ------
        tuple[int, _TokenType, str]
            ``(offset, token_type, value)`` triples whose offsets are
            relative to the start of the full document, suitable for
            ``get_tokens_unprocessed``.

        Notes
        -----
        Handles exactly three colons (``:::``). Four-or-more-colon
        variants (``::::{name}``) are a known MyST feature but are not
        currently in scope; if they appear later, capture the opening
        colon count and require the closing count to match via a
        backreference.

        Body content is emitted as plain ``Text`` (plus ``Name.Tag`` for
        option keys). MyST directive bodies vary by directive — e.g.
        ``:::{grid}`` carries sphinx-design markup, ``:::{tab-set}``
        carries inline content — so a single inner-language delegation
        is not appropriate. Specialized inner highlighting can be added
        per directive in a follow-up.

        Examples
        --------
        >>> tokens = tokenize_myst(
        ...     ":::{auto-pytest-plugin} my_project.pp\\n"
        ...     ":package: my-project\\n"
        ...     ":::\\n"
        ... )
        >>> any(":::{auto-pytest-plugin}" in v for _, v in tokens)
        True
        >>> any("Name.Tag" in tok and v == ":package:" for tok, v in tokens)
        True
        """  # noqa: D301 - backslashes are in doctest code, not escape sequences
        import re as _re

        yield match.start("opening"), String.Backtick, match.group("opening")
        yield match.start("newline"), Whitespace, match.group("newline")

        body = match.group("body")
        body_offset = match.start("body")
        # Walk the body line-by-line. Lines matching ``:<key>:[ <value>]``
        # tokenize the key as Name.Tag; everything else is Text.
        # Pattern: leading ``:``, identifier, trailing ``:``, then
        # optional whitespace + value through end of line.
        option_re = _re.compile(r"^(:[\w\-]+:)([^\n]*)(\n)", _re.MULTILINE)
        cursor = 0
        for option_match in option_re.finditer(body):
            # Emit any text between the previous match end and this
            # match's start as plain Text.
            if option_match.start() > cursor:
                preceding = body[cursor : option_match.start()]
                yield body_offset + cursor, Text, preceding
            yield (
                body_offset + option_match.start(1),
                Name.Tag,
                option_match.group(1),
            )
            value = option_match.group(2)
            if value:
                yield body_offset + option_match.start(2), Text, value
            yield (
                body_offset + option_match.start(3),
                Whitespace,
                option_match.group(3),
            )
            cursor = option_match.end()
        if cursor < len(body):
            yield body_offset + cursor, Text, body[cursor:]

        yield match.start("closing"), String.Backtick, match.group("closing")

    # tokens must be declared AFTER _handle_eval_rst because the class
    # body is executed sequentially and the dict literal references
    # _handle_eval_rst by name.
    tokens: t.ClassVar[dict[str, list[t.Any]]] = {
        "root": [
            # This rule MUST precede the inherited generic fenced-block
            # rule from MarkdownLexer: its language pattern [\w\-]+
            # cannot match {eval-rst}, so without this rule the entire
            # block falls through to plain Token.Text tokens.
            #
            # re.MULTILINE is inherited from MarkdownLexer.flags, so ^
            # matches at the start of each line (not just position 0).
            (
                # group opening: backtick fence + directive + optional
                # info string (e.g. ```{eval-rst} some-arg)
                (
                    r"(?P<opening>^```\{eval-rst\}[^\n]*)"
                    r"(?P<newline>\n)"
                    # group body: RST content, non-greedy to stop at first
                    # closing fence
                    r"(?P<body>(?:.|\n)*?)"
                    # group closing: bare ``` at start of line
                    r"(?P<closing>^```[ \t]*$\n?)"
                ),
                _handle_eval_rst,
            ),
            # Triple-colon fence (MyST colon_fence extension):
            # :::{<directive>}[ <info-string>] ... :::
            #
            # The MarkdownLexer parent has no rule for these so they
            # fall through to plain Token.Text without this handler.
            # Handles exactly three colons; four-or-more variants are
            # out of scope (see _handle_colon_fence Notes).
            (
                (
                    # group opening: ::: fence + braced directive name +
                    # optional info string (e.g. :::{tab-set} centered)
                    r"(?P<opening>^:::\{[\w\-]+\}[^\n]*)"
                    r"(?P<newline>\n)"
                    # group body: directive content, non-greedy to stop
                    # at the first closing fence
                    r"(?P<body>(?:.|\n)*?)"
                    # group closing: bare ::: at start of line
                    r"(?P<closing>^:::[ \t]*$\n?)"
                ),
                _handle_colon_fence,
            ),
            # All MarkdownLexer root rules follow unchanged, providing
            # highlighting for normal fenced code blocks, inline code,
            # headings, etc.
            *MarkdownLexer.tokens["root"],
        ],
        "inline": MarkdownLexer.tokens["inline"],
    }


def tokenize_myst(text: str) -> list[tuple[str, str]]:
    """Tokenize MyST source text, returning ``(token_type_str, value)`` pairs.

    Convenience wrapper around :class:`MystLexer` for tests and
    doctests. Token type strings are the standard Pygments string form,
    e.g. ``"Token.Literal.String.Backtick"``.

    Parameters
    ----------
    text : str
        MyST Markdown source text to tokenize.

    Returns
    -------
    list[tuple[str, str]]
        List of ``(str(token_type), value)`` pairs covering all tokens
        in the input, in document order.

    Examples
    --------
    >>> tokens = tokenize_myst("Hello world")
    >>> any("Hello" in v for _, v in tokens)
    True

    >>> tokens = tokenize_myst("```{eval-rst}\\nHello RST\\n```\\n")
    >>> ("Token.Literal.String.Backtick", "```{eval-rst}") in tokens
    True
    """  # noqa: D301 - backslashes are in doctest code, not escape sequences
    lexer = MystLexer()
    return [(str(tok), val) for tok, val in lexer.get_tokens(text)]
