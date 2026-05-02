"""Contract tests for the furo.ts <-> Tailwind CSS integration.

These tests assert that the selectors and class names furo.ts toggles
at runtime exist in the gp-furo-theme Tailwind v4 source CSS. They
catch the two failure modes that step 9.2's plugin fix illustrated:

1. Source-emission mismatch: CSS emits a selector that the JS toggle
   never sets (e.g. ``html[data-theme="dark"]`` while JS sets
   ``body.dataset.theme``).  Step 9.2 fixed exactly this case in the
   plugin.
2. Drift: refactor of either side independently breaks the contract
   without a typecheck-style guard.  These tests are that guard.

The tests read source ``.css`` files directly (not the Vite-compiled
output) so they don't require ``pnpm exec vite build`` to have run.
"""

from __future__ import annotations

import pathlib

import pytest

_WEB_STYLES = (
    pathlib.Path(__file__).resolve().parents[1]
    / "packages"
    / "gp-furo-theme"
    / "web"
    / "src"
    / "styles"
)
_INDEX_CSS = _WEB_STYLES / "index.css"
_BASE_CSS = _WEB_STYLES / "components" / "base.css"
_SCAFFOLD_CSS = _WEB_STYLES / "components" / "scaffold.css"


@pytest.fixture(scope="module")
def index_css_text() -> str:
    """Source content of web/src/styles/index.css."""
    return _INDEX_CSS.read_text()


@pytest.fixture(scope="module")
def base_css_text() -> str:
    """Source content of web/src/styles/components/base.css."""
    return _BASE_CSS.read_text()


@pytest.fixture(scope="module")
def scaffold_css_text() -> str:
    """Source content of web/src/styles/components/scaffold.css."""
    return _SCAFFOLD_CSS.read_text()


# ---------------------------------------------------------------------
# (1) html.show-back-to-top → .back-to-top { display: flex }
#
# furo.ts:39-43 toggles `.show-back-to-top` on document.documentElement
# (i.e. <html>) when the user scrolls past the configured threshold.
# scaffold.css must have a descendant rule that flips .back-to-top to
# display: flex.
# ---------------------------------------------------------------------


def test_scaffold_has_show_back_to_top_rule(scaffold_css_text: str) -> None:
    """Furo's back-to-top button only appears once html.show-back-to-top is set."""
    # Match flexibly — any whitespace, any trailing rules.
    assert ".show-back-to-top .back-to-top" in scaffold_css_text


def test_scaffold_has_back_to_top_default_hidden(scaffold_css_text: str) -> None:
    """Default state must hide the button; the .show-back-to-top rule reveals it."""
    # The .back-to-top base rule has display: none.  Without this default,
    # the button would always be visible.
    assert ".back-to-top" in scaffold_css_text
    # The string `display: none` must appear in scaffold.css somewhere
    # — the .back-to-top rule is one of several to use it.
    assert "display: none" in scaffold_css_text


# ---------------------------------------------------------------------
# (2) <body>.dataset.theme = "dark" → body[data-theme="dark"] {...}
#
# furo.ts:85 sets body.dataset.theme to one of "auto"/"light"/"dark".
# Three independent surfaces depend on this:
#   - The plugin's addBase() emits `body[data-theme="dark"] { --token: ... }`
#     and `@media (prefers-color-scheme: dark) body:not([data-theme="light"])`.
#     (Verified by tests/test_gp_furo_tokens — vitest plugin.test.ts.)
#   - base.css has `.only-light / .only-dark` visibility hooks scoped to
#     the body[data-theme=...] selector.
#   - base.css has theme-toggle SVG visibility rules
#     (one icon per data-theme state).
# ---------------------------------------------------------------------


def test_index_custom_variant_dark_binds_to_body_data_theme(
    index_css_text: str,
) -> None:
    """@custom-variant dark must target body[data-theme="dark"] (matching furo.ts)."""
    assert "@custom-variant dark" in index_css_text
    # The variant body must reference the body[data-theme="dark"] selector.
    assert 'body[data-theme="dark"]' in index_css_text


def test_base_has_only_light_only_dark_visibility(base_css_text: str) -> None:
    """body[data-theme=dark] must hide .only-light and show .only-dark."""
    assert 'body[data-theme="dark"] .only-dark' in base_css_text
    assert 'html body[data-theme="dark"] .only-light' in base_css_text


def test_base_has_theme_toggle_svg_rules(base_css_text: str) -> None:
    """Each data-theme state must drive a different .theme-toggle SVG icon."""
    # Three explicit data-theme values: auto, dark, light.
    assert 'body[data-theme="auto"] .theme-toggle' in base_css_text
    assert 'body[data-theme="dark"] .theme-toggle' in base_css_text
    assert 'body[data-theme="light"] .theme-toggle' in base_css_text


# ---------------------------------------------------------------------
# (3) <.mobile-header>.scrolled → border-bottom: none + box-shadow
#
# furo.ts:30-32 toggles `.scrolled` on the mobile header when the user
# scrolls.  scaffold.css must restyle the header's bottom edge.
# ---------------------------------------------------------------------


def test_scaffold_has_mobile_header_scrolled_rule(scaffold_css_text: str) -> None:
    """furo.ts adds .scrolled to .mobile-header on scroll — scaffold restyles it."""
    assert ".mobile-header.scrolled" in scaffold_css_text


# ---------------------------------------------------------------------
# (4) <html>.no-js → hide JS-driven UI affordances
#
# furo.ts:189 removes 'no-js' from documentElement once JS runs.  The
# template ships with `<html class="no-js">` so the theme toggle (etc.)
# stays hidden in JS-disabled environments.
# ---------------------------------------------------------------------


def test_scaffold_has_no_js_theme_toggle_rule(scaffold_css_text: str) -> None:
    """`.no-js .theme-toggle-container { display: none }` keeps the toggle out."""
    assert ".no-js .theme-toggle-container" in scaffold_css_text
