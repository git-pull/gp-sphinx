"""Regression tests for layout CSS rules."""

from __future__ import annotations

import pathlib

_LAYOUT_CSS = pathlib.Path(
    "packages/sphinx-ux-autodoc-layout/src/sphinx_ux_autodoc_layout/_static/css/layout.css"
)


def test_signature_expanded_uses_contents_layout() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert ".gp-sphinx-api-signature-expanded {\n  display: contents;\n}" in css


def test_api_header_defaults_to_center_alignment() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert "display: block;" not in css
    assert (
        "dl.gp-sphinx-api-container > dt.gp-sphinx-api-header {\n"
        "  display: flex;\n  align-items: center;\n"
    ) in css
    assert (
        "dl.gp-sphinx-api-container > dt.gp-sphinx-api-header > "
        ".gp-sphinx-api-layout--desktop {\n"
        "  display: flex;\n"
        "  align-items: center;\n"
    ) in css
    assert (
        "dl.gp-sphinx-api-container > dt.gp-sphinx-api-header "
        ".gp-sphinx-api-layout-left {\n"
        "  flex: 1 1 auto;\n"
        "  display: flex;\n"
        "  align-items: center;\n"
    ) in css
    assert (
        "dl.gp-sphinx-api-container > dt.gp-sphinx-api-header "
        ".gp-sphinx-api-layout-right {\n"
        "  display: flex;\n"
        "  align-items: center;\n"
    ) in css


def test_expanded_api_header_switches_back_to_top_alignment() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert (
        'dt.gp-sphinx-api-header[data-signature-expanded="true"] {\n'
        "  display: flex;\n"
        "  align-items: flex-start;\n"
        "}"
    ) in css
    assert (
        '> dt.gp-sphinx-api-header[data-signature-expanded="true"] > '
        ".gp-sphinx-api-layout--desktop {\n"
        "  align-items: flex-start;\n}" in css
    )
    assert (
        'dt.gp-sphinx-api-header[data-signature-expanded="true"] '
        ".gp-sphinx-api-layout-left {\n"
        "  align-items: flex-start;\n}" in css
    )
    assert (
        'dt.gp-sphinx-api-header[data-signature-expanded="true"] '
        ".gp-sphinx-api-layout-right {\n"
        "  align-items: flex-start;\n}" in css
    )


def test_layout_uses_container_query_for_variant_toggle() -> None:
    """Container query toggles desktop/mobile variant per inline-size.

    The toggle selectors are written with the same specificity as the
    layout rules (``dl.gp-sphinx-api-container > dt.gp-sphinx-api-header
    > .gp-sphinx-api-layout--{desktop,mobile}``) so the cascade order
    is preserved — ``@container`` does not bump specificity.
    """
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert "container-type: inline-size;" in css
    assert "container-name: gp-sphinx-api-entry;" in css
    assert "@container gp-sphinx-api-entry (max-width: 36rem) {" in css
    assert (
        "dl.gp-sphinx-api-container > dt.gp-sphinx-api-header > "
        ".gp-sphinx-api-layout--mobile,\n"
        ".gp-sphinx-api-card-shell > .gp-sphinx-api-card-entry > "
        ".gp-sphinx-api-header > .gp-sphinx-api-layout--mobile {\n"
        "  display: none;\n}"
    ) in css
    assert (
        "  dl.gp-sphinx-api-container > dt.gp-sphinx-api-header > "
        ".gp-sphinx-api-layout--desktop,\n"
        "  .gp-sphinx-api-card-shell > .gp-sphinx-api-card-entry > "
        ".gp-sphinx-api-header > .gp-sphinx-api-layout--desktop {\n"
        "    display: none;\n  }"
    ) in css
    assert (
        "  dl.gp-sphinx-api-container > dt.gp-sphinx-api-header > "
        ".gp-sphinx-api-layout--mobile,\n"
        "  .gp-sphinx-api-card-shell > .gp-sphinx-api-card-entry > "
        ".gp-sphinx-api-header > .gp-sphinx-api-layout--mobile {\n"
        "    display: flex;"
    ) in css


def test_layout_mobile_variant_uses_top_bottom_axes() -> None:
    """Mobile variant has its own top (toolbar) / bottom (signature) slots."""
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert (
        ".gp-sphinx-api-layout--mobile .gp-sphinx-api-layout-top {\n  display: flex;\n"
    ) in css
    assert (
        ".gp-sphinx-api-layout--mobile .gp-sphinx-api-layout-bottom {\n"
        "  display: flex;\n"
    ) in css
    assert (
        ".gp-sphinx-api-layout--mobile .gp-sphinx-api-source-link {\n"
        "  margin-left: auto;\n}"
    ) in css


def test_layout_drops_legacy_order_minus_one_hack() -> None:
    """Mobile variant has its own DOM order; no `order: -1` flex hack remains."""
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert "order: -1" not in css


def test_signature_multiline_list_uses_padding_indent() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert "padding-inline-start: var(--gp-sphinx-api-signature-indent, 1rem);" in css


def test_signature_multiline_list_clears_theme_dd_indent() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert "margin-inline-start: 0 !important;" in css
    assert "margin-left: 0 !important;" in css


def test_signature_css_does_not_force_sig_param_block_layout() -> None:
    css = _LAYOUT_CSS.read_text(encoding="utf-8")

    assert ".gp-sphinx-api-signature-expanded em.sig-param" not in css
