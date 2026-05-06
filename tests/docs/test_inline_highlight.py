"""Tests for the inline-highlight transform.

Validates the four content-pattern dispatchers (bare RST role,
RST role-with-content, shell session, inline RST directive) plus
the dimensional-invariant guarantee that the rendered output keeps
the ``<code class="docutils literal notranslate">`` outer wrapper.
"""

from __future__ import annotations

import pathlib
import sys
import typing as t

import pytest
from docutils import nodes

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "docs" / "_ext"))

import inline_highlight


class _PatternFixture(t.NamedTuple):
    """Fixture row for the ``_inline_html_for`` dispatcher."""

    test_id: str
    text: str
    expected_class: str | None
    expected_token_value: str | None


_PATTERN_FIXTURES: list[_PatternFixture] = [
    _PatternFixture(
        test_id="bare_rst_role_simple",
        text=":tool:",
        expected_class="na",
        expected_token_value=":tool:",
    ),
    _PatternFixture(
        test_id="bare_rst_role_namespaced",
        text=":argparse:program:",
        expected_class="na",
        expected_token_value=":argparse:program:",
    ),
    _PatternFixture(
        test_id="rst_role_with_content",
        text=":tool:`list_sessions`",
        expected_class="nv",
        expected_token_value="`list_sessions`",
    ),
    _PatternFixture(
        test_id="rst_namespaced_role_with_content",
        text=":argparse:program:`myapp`",
        expected_class="nv",
        expected_token_value="`myapp`",
    ),
    _PatternFixture(
        test_id="shell_session",
        text="$ uv run pytest",
        expected_class="gp",
        expected_token_value="$ ",
    ),
    _PatternFixture(
        test_id="inline_rst_directive",
        text=".. autodirective::",
        expected_class="ow",
        expected_token_value="autodirective",
    ),
    _PatternFixture(
        test_id="plain_prose_no_match",
        text="just some prose",
        expected_class=None,
        expected_token_value=None,
    ),
    _PatternFixture(
        test_id="plain_module_name_no_match",
        text="my_project.docs",
        expected_class=None,
        expected_token_value=None,
    ),
]


@pytest.mark.parametrize(
    list(_PatternFixture._fields),
    _PATTERN_FIXTURES,
    ids=[case.test_id for case in _PATTERN_FIXTURES],
)
def test_inline_html_for_dispatches_by_pattern(
    test_id: str,
    text: str,
    expected_class: str | None,
    expected_token_value: str | None,
) -> None:
    """``_inline_html_for`` returns the right tokens or ``None``."""
    rendered = inline_highlight._inline_html_for(text)
    if expected_class is None:
        assert rendered is None, f"{test_id}: expected None, got {rendered!r}"
        return
    assert rendered is not None
    assert f'class="{expected_class}"' in rendered, (
        f"{test_id}: expected class {expected_class!r} in {rendered!r}"
    )
    assert expected_token_value is not None  # narrow for mypy
    assert expected_token_value in rendered, (
        f"{test_id}: expected token value {expected_token_value!r} in {rendered!r}"
    )


def test_transform_preserves_code_outer_wrapper() -> None:
    """Replacement raw HTML keeps ``<code class="docutils literal notranslate">``.

    Dimensional invariant: Furo's inline-literal styling targets
    ``code.literal``. If the transform replaced ``<code>`` with
    ``<span>``, the box styling (background, padding, border-radius,
    font-size) would be lost and lines would warp. Verify the outer
    element is still ``<code>`` with the expected classes.
    """
    document = _make_document_with_literal(":tool:`list_sessions`")
    transform = inline_highlight.InlineHighlightTransform(document)
    transform.apply()

    raw_nodes = list(document.findall(nodes.raw))
    assert raw_nodes, "expected the literal to have been replaced with raw HTML"
    rendered = raw_nodes[0].astext()
    assert rendered.startswith('<code class="docutils literal notranslate highlight">')
    assert rendered.endswith("</code>")


def test_transform_skips_unmatched_literals() -> None:
    """A literal whose content matches no pattern stays untouched."""
    document = _make_document_with_literal("just plain prose here")
    transform = inline_highlight.InlineHighlightTransform(document)
    transform.apply()

    # The original literal node should still be in the document
    literals = list(document.findall(nodes.literal))
    assert len(literals) == 1
    assert literals[0].astext() == "just plain prose here"


def test_transform_skips_empty_literals() -> None:
    """An empty literal is not rewritten (would produce empty span output)."""
    document = _make_document_with_literal("")
    transform = inline_highlight.InlineHighlightTransform(document)
    transform.apply()

    raw_nodes = list(document.findall(nodes.raw))
    assert raw_nodes == []


def test_inline_formatter_strips_trailing_newline() -> None:
    r"""The custom formatter drops the trailing ``(Text, '\n')`` token.

    Without this, every inline span would emit a phantom ``<span>`` at
    the end, breaking visual tightness against subsequent prose.
    """
    rendered = inline_highlight._inline_html_for(":tool:`x`")
    assert rendered is not None
    # The output must not end with a newline (which would produce a
    # phantom whitespace span after Sphinx's writer wraps it).
    assert not rendered.endswith("\n")


def test_bare_rst_role_html_escapes_content() -> None:
    """The bare-role helper escapes HTML special characters defensively."""
    # Hypothetical edge case: a literal whose content matches the bare
    # role pattern but happens to contain a < or & character. The
    # current pattern won't match such content (regex restricts to
    # word + hyphen), but the escaping is still defensive.
    rendered = inline_highlight._bare_rst_role_html(":a&b:")
    assert "&amp;" in rendered


def _make_document_with_literal(text: str) -> nodes.document:
    """Build a minimal docutils document containing one ``nodes.literal``.

    Uses the canonical ``OptionParser(components=(Parser,))`` recipe to
    derive default settings, then ``new_document()`` to attach a reporter
    and source path. The returned document has everything
    ``Transform.apply`` needs to traverse and rewrite nodes.
    """
    import warnings

    from docutils.parsers.rst import Parser
    from docutils.utils import new_document

    with warnings.catch_warnings():
        # docutils' OptionParser triggers a DeprecationWarning since
        # 0.21 (replaced by argparse-based class). The replacement
        # isn't shipped yet upstream; suppress the warning until it is.
        warnings.simplefilter("ignore", DeprecationWarning)
        from docutils.frontend import OptionParser

        settings = OptionParser(components=(Parser,)).get_default_values()
    document = new_document("<test>", settings)
    paragraph = nodes.paragraph()
    paragraph += nodes.literal(text, text)
    document += paragraph
    return document
