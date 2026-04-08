"""Regression tests for layout CSS rules."""

from __future__ import annotations

import pathlib

_LAYOUT_CSS = pathlib.Path(
    "packages/sphinx-autodoc-layout/src/sphinx_autodoc_layout/_static/css/layout.css"
)


def test_signature_expanded_uses_contents_layout() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert ".api-signature-expanded {\n  display: contents;\n}" in css


def test_signature_multiline_list_uses_padding_indent() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert "padding-inline-start: var(--gal-signature-indent, 1rem);" in css


def test_signature_multiline_list_clears_theme_dd_indent() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert "margin-inline-start: 0 !important;" in css
    assert "margin-left: 0 !important;" in css


def test_signature_css_does_not_force_sig_param_block_layout() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert ".api-signature-expanded em.sig-param" not in css
