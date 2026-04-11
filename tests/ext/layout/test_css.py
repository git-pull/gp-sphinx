"""Regression tests for layout CSS rules."""

from __future__ import annotations

import pathlib

_LAYOUT_CSS = pathlib.Path(
    "packages/sphinx-autodoc-layout/src/sphinx_autodoc_layout/_static/css/layout.css"
)


def test_signature_expanded_uses_contents_layout() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert ".api-signature-expanded {\n  display: contents;\n}" in css


def test_api_header_defaults_to_center_alignment() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert (
        "dl.api-container > dt.api-header {\n  display: flex;\n  align-items: center;\n"
    ) in css
    assert "display: block;" not in css
    assert (
        "dl.api-container > dt.api-header > .api-layout {\n"
        "  display: flex;\n"
        "  align-items: center;\n"
    ) in css
    assert (
        "dl.api-container > dt.api-header .api-layout-left {\n"
        "  flex: 1 1 auto;\n"
        "  display: flex;\n"
        "  align-items: center;\n"
    ) in css
    assert (
        "dl.api-container > dt.api-header .api-layout-right {\n"
        "  display: flex;\n"
        "  align-items: center;\n"
    ) in css


def test_expanded_api_header_switches_back_to_top_alignment() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert (
        'dt.api-header[data-signature-expanded="true"] {\n'
        "  display: flex;\n"
        "  align-items: flex-start;\n"
        "}"
    ) in css
    assert (
        '> dt.api-header[data-signature-expanded="true"] > .api-layout {\n'
        "  align-items: flex-start;\n}" in css
    )
    assert (
        'dt.api-header[data-signature-expanded="true"] .api-layout-left {\n'
        "  align-items: flex-start;\n}" in css
    )
    assert (
        'dt.api-header[data-signature-expanded="true"] .api-layout-right {\n'
        "  align-items: flex-start;\n}" in css
    )


def test_signature_multiline_list_uses_padding_indent() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert "padding-inline-start: var(--api-signature-indent, 1rem);" in css


def test_signature_multiline_list_clears_theme_dd_indent() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert "margin-inline-start: 0 !important;" in css
    assert "margin-left: 0 !important;" in css


def test_signature_css_does_not_force_sig_param_block_layout() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert ".api-signature-expanded em.sig-param" not in css
