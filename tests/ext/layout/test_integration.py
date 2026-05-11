"""Integration tests for sphinx_ux_autodoc_layout HTML output."""

from __future__ import annotations

import re

import pytest


def _extract_init_header(html: str) -> str:
    """Return the full ``LayoutDemo.__init__`` header fragment."""
    init_match = re.search(
        r'(<dt (?=[^>]*class="[^"]*gp-sphinx-api-header[^"]*")'
        r'(?=[^>]*id="api_demo_layout\.LayoutDemo\.__init__")[^>]*>.*?</dt>)',
        html,
        re.DOTALL,
    )
    assert init_match is not None
    return init_match.group(1).strip()


@pytest.mark.integration
def test_layout_demo_renders_api_component_contract(layout_default_html: str) -> None:
    html = layout_default_html

    assert re.search(r'<dl class="[^"]*gp-sphinx-api-container[^"]*">', html)
    assert re.search(r'<dd class="[^"]*gp-sphinx-api-content[^"]*">', html)
    assert (
        'class="gp-sphinx-api-description gp-sphinx-api-region gp-sphinx-api-region--narrative"'
        in html
    )
    assert (
        'class="gp-sphinx-api-parameters gp-sphinx-api-region gp-sphinx-api-region--fields"'
        in html
    )
    assert (
        'class="gp-sphinx-api-footer gp-sphinx-api-region gp-sphinx-api-region--members"'
        in html
    )
    assert '<details class="gp-sphinx-api-fold gp-sphinx-api-fold--parameters">' in html
    assert 'class="gp-sphinx-api-sig-fold"' not in html

    init_html = _extract_init_header(html)

    assert 'data-signature-expanded="false"' in init_html
    assert '<div class="gp-sphinx-api-layout" data-signature-expanded=' not in init_html
    assert re.search(
        r'<dt [^>]*class="[^"]*gp-sphinx-api-header[^"]*"[^>]*data-signature-expanded="false"',
        init_html,
    )
    assert "gp-sphinx-api-layout--desktop" in init_html
    assert "gp-sphinx-api-layout--mobile" in init_html
    assert 'class="gp-sphinx-api-layout-left"' in init_html
    assert 'class="gp-sphinx-api-layout-right gp-sphinx-toolbar"' in init_html
    assert 'class="gp-sphinx-api-signature"' in init_html
    assert 'class="headerlink gp-sphinx-api-link"' in init_html
    assert 'class="gp-sphinx-api-badge-container"' in init_html
    assert 'class="gp-sphinx-api-source-link"' in init_html
    assert (
        'class="gp-sphinx-api-signature-expanded gp-sphinx-api-sig-expanded"'
        in init_html
    )
    assert (
        'aria-controls="api_demo_layout.LayoutDemo.__init__--signature-expanded-desktop"'
        in init_html
    )
    assert (
        'aria-controls="api_demo_layout.LayoutDemo.__init__--signature-expanded-mobile"'
        in init_html
    )
    assert (
        'id="api_demo_layout.LayoutDemo.__init__--signature-expanded-desktop"'
        in init_html
    )
    assert (
        'id="api_demo_layout.LayoutDemo.__init__--signature-expanded-mobile"'
        in init_html
    )
    assert "<dl>" in init_html
    assert '<span class="sig-paren">(</span>' in init_html
    assert '<span class="sig-paren">)</span>' in init_html
    assert 'class="gp-sphinx-api-sig-collapse"' in init_html
    assert "[collapse]" in init_html
    assert re.search(
        r'<span class="sig-paren">\)</span>\s*<button[^>]*class="[^"]*gp-sphinx-api-sig-collapse[^"]*"',
        init_html,
    )
    assert "host" in init_html
    assert "port" in init_html
    assert "str" in init_html
    assert "int" in init_html
    assert "[source]" in init_html
    assert "gp-sphinx-api-signature-panel" not in init_html
