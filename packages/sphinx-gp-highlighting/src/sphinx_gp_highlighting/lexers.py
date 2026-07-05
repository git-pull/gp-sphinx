"""Pygments lexers for documentation-focused code blocks."""

from __future__ import annotations

import re
import typing as t

from pygments.lexer import RegexLexer
from pygments.token import Comment, Name, Punctuation, Text, Whitespace


class DirectoryTreeLexer(RegexLexer):
    r"""Lexer for ``tree(1)``-style directory listings.

    The lexer targets documentation snippets that show project layouts
    with box-drawing connectors. It deliberately uses standard Pygments
    token types so existing Sphinx styles can colour the output without
    package-specific token CSS.

    Examples
    --------
    >>> from pygments.token import Token
    >>> lexer = DirectoryTreeLexer()
    >>> tokens = list(lexer.get_tokens("root\\n└── pyproject.toml  # config\\n"))
    >>> (Token.Punctuation, '└──') in tokens
    True
    >>> (Token.Name, 'pyproject.toml') in tokens
    True
    >>> (Token.Comment.Single, '# config') in tokens
    True
    """

    name = "Directory tree"
    aliases = ["tree", "directory-tree", "dir-tree"]  # noqa: RUF012
    filenames: t.ClassVar[list[str]] = []
    mimetypes = ["text/x-directory-tree"]  # noqa: RUF012

    tokens = {  # noqa: RUF012
        "root": [
            (r"\n", Whitespace),
            (r"[ \t]+", Whitespace),
            (r"(?:├──|└──|│)", Punctuation),
            (r"#.*$", Comment.Single),
            (r"[^/\s#]+/", Name.Namespace),
            (r"[^/\s#.]+\.[^/\s#]+", Name),
            (r"[^/\s#]+", Name.Namespace),
            (r".", Text),
        ],
    }

    @staticmethod
    def analyse_text(text: str) -> float:
        r"""Return a confidence score for tree-like text.

        Parameters
        ----------
        text : str
            Source text to inspect.

        Returns
        -------
        float
            ``0.7`` when box-drawing tree connectors are present,
            otherwise ``0.0``.

        Examples
        --------
        >>> DirectoryTreeLexer.analyse_text("root\\n└── pyproject.toml\\n")
        0.7
        >>> DirectoryTreeLexer.analyse_text("plain text")
        0.0
        """
        if re.search(r"(?m)^[│ \t]*(?:├──|└──)\s+\S", text):
            return 0.7
        return 0.0
