"""Type stubs for pygments.lexers.markup (RstLexer and MarkdownLexer).

Only the symbols used by gp_sphinx.myst_lexer are covered here.
"""

from collections.abc import Iterable, Iterator
from typing import Any, ClassVar

from pygments.lexer import RegexLexer
from pygments.token import _TokenType

class RstLexer(RegexLexer):
    name: ClassVar[str]
    aliases: ClassVar[list[str]]
    filenames: ClassVar[list[str]]
    mimetypes: ClassVar[list[str]]
    handlecodeblocks: bool

    def __init__(
        self,
        *,
        handlecodeblocks: bool = ...,
        stripnl: bool = ...,
        **options: object,
    ) -> None: ...
    def get_tokens_unprocessed(
        self,
        text: str,
        stack: Iterable[str] = ...,
    ) -> Iterator[tuple[int, _TokenType, str]]: ...

class MarkdownLexer(RegexLexer):
    name: ClassVar[str]
    aliases: ClassVar[list[str]]
    filenames: ClassVar[list[str]]
    mimetypes: ClassVar[list[str]]
    tokens: ClassVar[dict[str, list[Any]]]

    def __init__(self, **options: object) -> None: ...
    def get_tokens_unprocessed(
        self,
        text: str,
        stack: Iterable[str] = ...,
    ) -> Iterator[tuple[int, _TokenType, str]]: ...
