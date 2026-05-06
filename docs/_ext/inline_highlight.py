"""Inline syntax highlighting for ``nodes.literal`` (single-backtick code).

Sphinx + MyST send single-backtick inline code to docutils as
:class:`docutils.nodes.literal`, which renders as
``<code class="docutils literal notranslate"><span class="pre">…</span></code>``
with no Pygments invocation. Block-level fences (``rst``/``myst``)
go through Pygments; inline literals don't. This is upstream-default
Sphinx behavior.

This transform restores parity for the four inline content patterns
the workspace's reference + kitchen-sink pages rely on:

- **Bare RST roles** like ``:argparse:program:`` / ``:tool:`` —
  Pygments' :class:`RstLexer` does not tokenize bare role names
  (without a backtick body), so we emit a single ``Name.Attribute``
  span explicitly.
- **RST roles with content** like ``:tool:`list_sessions``` —
  :class:`RstLexer` tokenizes these as ``Name.Attribute`` +
  ``Name.Variable``.
- **Shell sessions** like ``$ uv run pytest`` — :class:`BashSessionLexer`
  tokenizes the ``$`` prompt as ``Generic.Prompt``.
- **Inline RST directive references** like ``.. autodirective::`` —
  :class:`RstLexer` tokenizes ``..`` / directive name / ``::``.

Dimensional invariants
----------------------
The transform PRESERVES the outer ``<code class="docutils literal
notranslate">`` wrapper that Sphinx emits for ``nodes.literal``.
Furo's inline-literal styling targets ``code.literal, .sig-inline``
in ``furo.css`` (background, border-radius, font-size, padding) — by
keeping ``<code>`` as the outer element, the existing box styling
applies unchanged. Pygments token spans inside add foreground color
only (no padding/margin), so line height, line wrapping, and span
width are identical to pre-transform.

Inspired by :class:`django_docutils.lib.transforms.code.CodeTransform`,
which establishes the precedent of post-parse pattern dispatch over
``nodes.literal``.
"""

from __future__ import annotations

import html
import io
import re
import typing as t

from docutils import nodes
from docutils.transforms import Transform
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.markup import RstLexer
from pygments.lexers.shell import BashSessionLexer
from pygments.token import Token

if t.TYPE_CHECKING:
    from pygments.lexer import Lexer
    from sphinx.application import Sphinx


# Pattern detectors run in order; first match wins. Anchored at start
# AND end of string (the literal's full text) so prose containing a
# stray ``:foo:`` substring elsewhere in a sentence cannot trigger
# false positives — only inline literals whose ENTIRE content matches
# one of these shapes get highlighted.

# Bare RST role / option / directive-attribute name like ``:tool:``,
# ``:argparse:program:``, ``:package:``. Word characters and hyphens
# only between the colons.
_BARE_RST_ROLE_RE = re.compile(r"^:[\w-]+(?::[\w-]+)*:$")

# RST role with a backtick body: ``:tool:`list_sessions```,
# ``:argparse:program:`myapp```. Body content is permissive (any non-
# backtick run) since RstLexer handles whatever's inside.
_RST_ROLE_WITH_CONTENT_RE = re.compile(r"^:[\w-]+(?::[\w-]+)*:`[^`]+`$")

# Shell session: starts with ``$ ``. Single line — inline literals
# can't span multiple lines, but we replace any embedded ``\n`` with a
# space defensively (django-docutils precedent).
_SHELL_SESSION_RE = re.compile(r"^\$ ")

# Inline RST directive reference: ``.. <name>::`` optionally followed
# by an argument. The two leading dots + the name + the closing ``::``
# are the recognizable shape.
_INLINE_RST_DIRECTIVE_RE = re.compile(r"^\.\.\s+[\w-]+::")


class _InlineFormatter(HtmlFormatter[str]):
    r"""Pygments HTML formatter tuned for inline output.

    With ``nowrap=True`` the formatter emits raw ``<span>`` tokens with
    no surrounding ``<pre>`` or ``<div>``. This override additionally
    strips the trailing ``(Token.Text, '\n')`` that every Pygments
    lexer appends at end-of-stream — that newline would render as a
    phantom whitespace span tight against the closing ``</code>`` tag
    in inline contexts. Pattern lifted from
    :class:`django_docutils.lib.transforms.code.InlineHtmlFormatter`.
    """

    def format_unencoded(
        self,
        tokensource: t.Iterable[tuple[t.Any, str]],
        outfile: t.Any,
    ) -> None:
        """Trim the trailing newline token before delegating to ``HtmlFormatter``."""
        tokens = list(tokensource)
        if tokens and tokens[-1] == (Token.Text, "\n"):
            tokens = tokens[:-1]
        super().format_unencoded(iter(tokens), outfile)


_FORMATTER = _InlineFormatter(nowrap=True)


def _highlight(text: str, lexer: Lexer) -> str:
    """Return inner pygments span markup for ``text`` tokenized by ``lexer``."""
    out = io.StringIO()
    _FORMATTER.format(lexer.get_tokens(text), out)
    return out.getvalue().rstrip("\n")


def _detect_lexer(text: str) -> Lexer | None:
    """Return the pygments lexer that should tokenize ``text``, or ``None``.

    Returns ``None`` when no pattern matches — caller leaves the
    ``nodes.literal`` unchanged in that case.

    Examples
    --------
    >>> _detect_lexer(":tool:`list_sessions`").__class__.__name__
    'RstLexer'
    >>> _detect_lexer("$ uv run pytest").__class__.__name__
    'BashSessionLexer'
    >>> _detect_lexer(".. autodirective::").__class__.__name__
    'RstLexer'
    >>> _detect_lexer("just plain prose") is None
    True
    """
    if _SHELL_SESSION_RE.match(text):
        return BashSessionLexer()
    if _RST_ROLE_WITH_CONTENT_RE.match(text):
        return RstLexer()
    if _INLINE_RST_DIRECTIVE_RE.match(text):
        return RstLexer()
    return None


def _bare_rst_role_html(text: str) -> str:
    """Wrap a bare RST role token in a ``Name.Attribute`` (``na``) span.

    :class:`RstLexer` does not recognize bare ``:role:`` patterns
    (without a backtick body) — it tokenizes them as plain ``Token.Text``.
    Emit the ``Name.Attribute`` span explicitly so the ``Role`` columns
    in package reference tables get the same colored treatment as the
    matching ``Example`` columns.

    Examples
    --------
    >>> _bare_rst_role_html(":tool:")
    '<span class="na">:tool:</span>'
    >>> _bare_rst_role_html(":argparse:program:")
    '<span class="na">:argparse:program:</span>'
    """
    return f'<span class="na">{html.escape(text)}</span>'


def _inline_html_for(text: str) -> str | None:
    """Return the inner HTML for ``text`` (token spans), or ``None``.

    ``None`` signals "no pattern matched, leave the literal alone."
    """
    if _BARE_RST_ROLE_RE.match(text):
        return _bare_rst_role_html(text)
    lexer = _detect_lexer(text)
    if lexer is None:
        return None
    return _highlight(text, lexer)


class InlineHighlightTransform(Transform):
    """Apply Pygments highlighting to ``nodes.literal`` matching known shapes.

    Walks every ``nodes.literal`` in the resolved doctree, dispatches by
    content pattern (see module docstring), and replaces matched nodes
    with ``nodes.raw`` containing ``<code class="docutils literal
    notranslate highlight">…spans…</code>``. The outer ``<code>`` element
    is preserved so Furo's existing inline-literal box styling applies
    unchanged — pygments tokens add color only.

    Priority 120 follows the
    :class:`django_docutils.lib.transforms.code.CodeTransform` precedent
    — runs after docutils' default transforms but before the writer.
    """

    default_priority = 120

    def apply(self, **kwargs: t.Any) -> None:
        """Walk literals, replace matched ones with token-span raw HTML."""
        for node in list(self.document.findall(nodes.literal)):
            text = node.astext()
            if not text:
                continue
            # Inline literals can't span lines, but defensive normalize
            # — docutils sometimes leaks newlines from soft-wrapped
            # source. Match the django-docutils CodeTransform behavior.
            normalized = text.strip().replace("\n", " ")

            inner = _inline_html_for(normalized)
            if inner is None:
                continue

            wrapped = (
                f'<code class="docutils literal notranslate highlight">{inner}</code>'
            )
            replacement = nodes.raw("", wrapped, format="html")
            if node.parent is not None:
                node.replace_self(replacement)


def setup(app: Sphinx) -> dict[str, object]:
    """Register :class:`InlineHighlightTransform` with Sphinx.

    Examples
    --------
    >>> class _FakeApp:
    ...     transforms: t.ClassVar[list[type]] = []
    ...     def add_transform(self, cls: type) -> None:
    ...         self.transforms.append(cls)
    >>> app = _FakeApp()
    >>> meta = setup(app)  # type: ignore[arg-type]
    >>> InlineHighlightTransform in app.transforms
    True
    >>> meta["parallel_read_safe"]
    True
    """
    app.add_transform(InlineHighlightTransform)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
