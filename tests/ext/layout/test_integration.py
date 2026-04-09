"""Integration tests for sphinx_autodoc_layout HTML output."""

from __future__ import annotations

import re

import pytest


def _extract_init_header(html: str) -> str:
    """Return the full ``LayoutDemo.__init__`` header fragment."""
    init_match = re.search(
        r'(<dt (?=[^>]*class="[^"]*api-header[^"]*")'
        r'(?=[^>]*id="gal_demo_api\.LayoutDemo\.__init__")[^>]*>.*?</dt>)',
        html,
        re.DOTALL,
    )
    assert init_match is not None
    return init_match.group(1).strip()


@pytest.mark.integration
def test_layout_demo_renders_api_component_contract(layout_default_html: str) -> None:
    html = layout_default_html

    assert re.search(r'<dl class="[^"]*api-container[^"]*">', html)
    assert re.search(r'<dd class="[^"]*api-content[^"]*">', html)
    assert 'class="api-description gal-region gal-region--narrative"' in html
    assert 'class="api-parameters gal-region gal-region--fields"' in html
    assert 'class="api-footer gal-region gal-region--members"' in html
    assert '<details class="gal-fold gal-fold--parameters">' in html
    assert 'class="gal-sig-fold"' not in html

    init_html = _extract_init_header(html)

    assert 'data-signature-expanded="false"' in init_html
    assert '<div class="api-layout" data-signature-expanded=' not in init_html
    assert re.search(
        r'<dt [^>]*class="[^"]*api-header[^"]*"[^>]*data-signature-expanded="false"',
        init_html,
    )
    assert 'class="api-layout"' in init_html
    assert 'class="api-layout-left"' in init_html
    assert 'class="api-layout-right sab-toolbar"' in init_html
    assert 'class="api-signature"' in init_html
    assert 'class="headerlink api-link"' in init_html
    assert 'class="api-badge-container"' in init_html
    assert 'class="api-source-link"' in init_html
    assert 'class="api-signature-expanded gal-sig-expanded"' in init_html
    assert (
        'aria-controls="gal_demo_api.LayoutDemo.__init__--signature-expanded"'
        in init_html
    )
    assert 'id="gal_demo_api.LayoutDemo.__init__--signature-expanded"' in init_html
    assert "<dl>" in init_html
    assert '<span class="sig-paren">(</span>' in init_html
    assert '<span class="sig-paren">)</span>' in init_html
    assert 'class="gal-sig-collapse"' in init_html
    assert "[collapse]" in init_html
    assert re.search(
        r'<span class="sig-paren">\)</span>\s*<button[^>]*class="[^"]*gal-sig-collapse[^"]*"',
        init_html,
    )
    assert "host" in init_html
    assert "port" in init_html
    assert "str" in init_html
    assert "int" in init_html
    assert "[source]" in init_html
    assert "api-signature-panel" not in init_html
