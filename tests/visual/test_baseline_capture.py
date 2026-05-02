"""Capture Playwright visual baselines from the SCSS-compiled gp-furo build.

These baselines pin "what visual parity means" before step 9 begins
re-authoring the CSS in pure Tailwind v4. The regression suite in
step 9.11 will diff every step-9 build against these stored
baselines; documented per-page residuals exceeding 0.1% need
rationale, exceeding 0.5% need a fix.

12 representative pages x 2 modes (light/dark) x 3 viewports
(mobile/tablet/desktop) = 72 PNGs under
``tests/visual/__snapshots__/baseline-scss/``.

Idempotent: re-running the test file is a no-op once the baselines
exist. To re-capture, delete the matching files (or the whole
directory).

Run via:

    GP_SPHINX_VISUAL=1 uv run pytest tests/visual/test_baseline_capture.py -vvv

Default ``py.test`` runs skip these (gated by ``GP_SPHINX_VISUAL``).
"""

from __future__ import annotations

import os
import pathlib
import typing as t

import pytest
from playwright.sync_api import Page

_BASELINE_DIR = (
    pathlib.Path(__file__).resolve().parent / "__snapshots__" / "baseline-scss"
)
_SKIP_REASON = "Set GP_SPHINX_VISUAL=1 to enable visual capture tests"

# Disable animations + transitions during capture so frame timing doesn't
# leak into PNG bytes. `scroll-behavior: auto` defeats Furo's smooth-scroll
# (otherwise capture-time scroll on `:target` anchors is animated).
_DISABLE_ANIMATIONS_CSS = """
*, *::before, *::after {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
    transition-duration: 0s !important;
    transition-delay: 0s !important;
    scroll-behavior: auto !important;
}
"""


class _VisualCase(t.NamedTuple):
    """One baseline capture: page x theme x viewport."""

    test_id: str
    page_path: str
    theme: t.Literal["light", "dark"]
    viewport_width: int
    viewport_height: int


# 12 pages chosen for surface coverage: prose-heavy, code-heavy, table-heavy,
# sidebar-tree-heavy, footnote-heavy, image-heavy, etc.  Paths use dirhtml-
# style trailing slashes; the http.server fixture resolves to index.html.
_PAGES: list[tuple[str, str]] = [
    ("home", "/"),
    ("api", "/api/"),
    ("config", "/configuration/"),
    ("pkg-furo", "/packages/gp-furo-theme/"),
    ("pkg-spgt", "/packages/sphinx-gp-theme/"),
    ("gallery", "/gallery/"),
    ("quickstart", "/quickstart/"),
    ("argparse", "/argparse-programsindex/"),
    ("arch", "/architecture/"),
    ("whatsnew", "/whats-new/"),
    ("search", "/search/"),
    ("genindex", "/genindex/"),
]
_THEMES: tuple[t.Literal["light", "dark"], ...] = ("light", "dark")
_VIEWPORTS: tuple[tuple[str, int, int], ...] = (
    ("mobile", 600, 800),
    ("tablet", 1024, 768),
    ("desktop", 1440, 900),
)


def _build_cases() -> list[_VisualCase]:
    cases: list[_VisualCase] = []
    for page_id, page_path in _PAGES:
        for theme in _THEMES:
            for vp_id, vw, vh in _VIEWPORTS:
                cases.append(
                    _VisualCase(
                        test_id=f"{page_id}-{theme}-{vp_id}",
                        page_path=page_path,
                        theme=theme,
                        viewport_width=vw,
                        viewport_height=vh,
                    ),
                )
    return cases


_CASES: list[_VisualCase] = _build_cases()


@pytest.mark.skipif(
    not os.environ.get("GP_SPHINX_VISUAL"),
    reason=_SKIP_REASON,
)
@pytest.mark.parametrize(
    list(_VisualCase._fields),
    _CASES,
    ids=[c.test_id for c in _CASES],
)
def test_capture_baseline(
    test_id: str,
    page_path: str,
    theme: t.Literal["light", "dark"],
    viewport_width: int,
    viewport_height: int,
    page: Page,
    http_server_url: str,
) -> None:
    """Capture one baseline screenshot for (page, theme, viewport).

    Idempotent: returns early if the target PNG already exists.
    """
    _BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    target = _BASELINE_DIR / f"{test_id}.png"
    if target.exists() and target.stat().st_size > 0:
        return

    page.set_viewport_size({"width": viewport_width, "height": viewport_height})

    # Force theme before any scripts run so Furo's `_html_page_context` /
    # furo.ts theme-init reads our value rather than the OS preference.
    page.add_init_script(
        f"document.documentElement.dataset.theme = {theme!r};"
        f"document.addEventListener('DOMContentLoaded', () => {{"
        f"  document.body.dataset.theme = {theme!r};"
        f"}});",
    )
    page.goto(f"{http_server_url}{page_path}")
    page.wait_for_load_state("networkidle")

    # Pin theme one more time after JS has run (furo.ts may have flipped it).
    page.evaluate(f"document.body.dataset.theme = {theme!r};")

    # Disable animations *after* navigation so injected styles win the
    # cascade against Furo's own rules.
    page.add_style_tag(content=_DISABLE_ANIMATIONS_CSS)

    # Wait for fonts; otherwise a fallback render leaks into the PNG.
    page.evaluate("document.fonts.ready")

    page.screenshot(path=str(target), full_page=True)
    assert target.exists()
    assert target.stat().st_size > 0
