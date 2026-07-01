"""Tripwire keeping the mermaid palettes in sync with gp-furo-tokens.

Mermaid bakes literal colours into rendered SVGs, so the extension carries
hex copies of the gp-furo token values — CSS custom properties cannot reach
inside ``mmdc``. These tests scrape ``light.ts``/``dark.ts`` at test time so
a token retune fails here instead of drifting silently.
"""

from __future__ import annotations

import pathlib
import re
import typing as t

import pytest

import sphinx_gp_mermaid as sgm

_TOKENS_SRC = pathlib.Path(__file__).parents[3] / "packages" / "gp-furo-tokens" / "src"

_TOKEN_RE = re.compile(r'"(--[\w-]+)":\s*"([^"]+)"')

#: CSS colour keywords the token files use where the palette stores hex.
_KEYWORD_HEX = {
    "black": "#000000",
    "white": "#ffffff",
}


def _load_tokens(filename: str) -> dict[str, str]:
    """Return custom-property values scraped from a gp-furo-tokens TS file."""
    contents = (_TOKENS_SRC / filename).read_text(encoding="utf-8")
    return {
        name: _KEYWORD_HEX.get(value.lower(), value).lower()
        for name, value in _TOKEN_RE.findall(contents)
    }


class PaletteSyncCase(t.NamedTuple):
    """One mermaid themeVariable and the gp-furo token it must equal."""

    test_id: str
    palette_key: str
    token_name: str


_PALETTE_SYNC_CASES: list[PaletteSyncCase] = [
    PaletteSyncCase(
        test_id="primary-color",
        palette_key="primaryColor",
        token_name="--color-background-secondary",
    ),
    PaletteSyncCase(
        test_id="primary-border-color",
        palette_key="primaryBorderColor",
        token_name="--color-brand-primary",
    ),
    PaletteSyncCase(
        test_id="primary-text-color",
        palette_key="primaryTextColor",
        token_name="--color-foreground-primary",
    ),
    PaletteSyncCase(
        test_id="line-color",
        palette_key="lineColor",
        token_name="--color-foreground-muted",
    ),
    PaletteSyncCase(
        test_id="text-color",
        palette_key="textColor",
        token_name="--color-foreground-primary",
    ),
    PaletteSyncCase(
        test_id="background",
        palette_key="background",
        token_name="--color-background-primary",
    ),
    PaletteSyncCase(
        test_id="edge-label-background",
        palette_key="edgeLabelBackground",
        token_name="--color-background-secondary",
    ),
    PaletteSyncCase(
        test_id="secondary-color",
        palette_key="secondaryColor",
        token_name="--color-background-primary",
    ),
    PaletteSyncCase(
        test_id="tertiary-color",
        palette_key="tertiaryColor",
        token_name="--color-background-secondary",
    ),
]

_THEME_TOKEN_FILES = {
    sgm._THEME_LIGHT: "light.ts",
    sgm._THEME_DARK: "dark.ts",
}


@pytest.mark.parametrize(
    "case",
    _PALETTE_SYNC_CASES,
    ids=[c.test_id for c in _PALETTE_SYNC_CASES],
)
@pytest.mark.parametrize("theme", [sgm._THEME_LIGHT, sgm._THEME_DARK])
def test_palette_matches_gp_furo_tokens(theme: str, case: PaletteSyncCase) -> None:
    """Every colour in ``_PALETTES`` equals its gp-furo token value."""
    tokens = _load_tokens(_THEME_TOKEN_FILES[theme])
    assert case.token_name in tokens, (
        f"{case.token_name} not found in {_THEME_TOKEN_FILES[theme]}; "
        "the token was renamed or the scrape regex no longer matches"
    )
    palette_value = sgm._PALETTES[theme][case.palette_key].lower()
    assert palette_value == tokens[case.token_name], (
        f"{theme} palette {case.palette_key}={palette_value} out of sync with "
        f"{case.token_name}={tokens[case.token_name]}; update _PALETTES and "
        "bump _RENDER_VERSION"
    )


def test_every_palette_colour_is_covered() -> None:
    """Each non-font palette key has a sync case, so new keys can't drift."""
    covered = {case.palette_key for case in _PALETTE_SYNC_CASES}
    for theme, palette in sgm._PALETTES.items():
        colour_keys = {key for key in palette if key != "fontFamily"}
        assert colour_keys == covered, (
            f"{theme}: uncovered keys {colour_keys - covered}"
        )
