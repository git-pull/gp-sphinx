"""Regression tests for layout JS behavior contracts."""

from __future__ import annotations

import pathlib

_LAYOUT_JS = pathlib.Path(
    "packages/sphinx-ux-autodoc-layout"
    "/src/sphinx_ux_autodoc_layout/_static/js/layout.js",
)


def test_scroll_into_view_does_not_center() -> None:
    """expandForHash must not override scroll-margin-top with block center."""
    js = _LAYOUT_JS.read_text(encoding="utf-8")

    assert "block: 'center'" not in js, (
        "layout.js must not use scrollIntoView({ block: 'center' }); "
        "use scrollIntoView() to respect CSS scroll-margin-top"
    )
    assert 'block: "center"' not in js, (
        'layout.js must not use scrollIntoView({ block: "center" }); '
        "use scrollIntoView() to respect CSS scroll-margin-top"
    )


def test_expand_for_hash_calls_scroll_into_view() -> None:
    """expandForHash must still call scrollIntoView to scroll to target."""
    js = _LAYOUT_JS.read_text(encoding="utf-8")

    assert "scrollIntoView()" in js
