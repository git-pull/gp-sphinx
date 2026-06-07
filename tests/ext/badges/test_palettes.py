"""Contract tests for the shared badge palette stylesheet.

``sab_palettes.css`` declares its own invariants: the
``body[data-theme="dark"]`` block holds "Identical values to the
``@media`` block above", and every colour class reads tokens that the
light-mode ``:root`` block defines. Drift between the blocks is
invisible at build time, so these tests parse the stylesheet as text
and pin the contracts down.
"""

from __future__ import annotations

import pathlib
import re

import sphinx_ux_badges

_PALETTES_PATH = (
    pathlib.Path(sphinx_ux_badges.__file__).parent
    / "_static"
    / "css"
    / "sab_palettes.css"
)

_DECLARATION = re.compile(r"(--gp-sphinx-badge-[\w-]+):\s*([^;]+);")
_VAR_REFERENCE = re.compile(r"var\((--gp-sphinx-badge-[\w-]+)\)")
_TOKEN_SUFFIX = re.compile(r"-(bg|fg|border)$")

_ROOT_BLOCK = re.compile(r":root \{(.*?)\n\}", re.S)
_MEDIA_DARK_BLOCK = re.compile(
    r"@media \(prefers-color-scheme: dark\) \{(.*?)\n\}\n",
    re.S,
)
_BODY_DARK_BLOCK = re.compile(r'\nbody\[data-theme="dark"\] \{(.*?)\n\}', re.S)


def _palette_css() -> str:
    """Return the palette stylesheet source."""
    return _PALETTES_PATH.read_text(encoding="utf-8")


def _block(css: str, pattern: re.Pattern[str]) -> str:
    """Return the body of the first block matching *pattern*."""
    match = pattern.search(css)
    assert match is not None, f"palette block not found: {pattern.pattern}"
    return match.group(1)


def _declarations(block: str) -> dict[str, str]:
    """Return ``token -> value`` declarations inside *block*."""
    return {token: value.strip() for token, value in _DECLARATION.findall(block)}


def _families(tokens: dict[str, str]) -> set[str]:
    """Return token families (the prefix before ``-bg``/``-fg``/``-border``)."""
    return {_TOKEN_SUFFIX.sub("", token) for token in tokens}


def test_dark_blocks_are_identical() -> None:
    """The two dark-mode blocks declare identical token/value pairs.

    The ``body[data-theme="dark"]`` block's own comment promises
    "Identical values to the ``@media`` block above"; a token present
    in only one block silently renders light-mode colours for one of
    the two dark-mode entry paths.
    """
    css = _palette_css()
    media_dark = _declarations(_block(css, _MEDIA_DARK_BLOCK))
    body_dark = _declarations(_block(css, _BODY_DARK_BLOCK))

    assert media_dark == body_dark, (
        "dark-mode palette blocks diverged; "
        f"only in @media: {sorted(set(media_dark) - set(body_dark))}, "
        f"only in body[data-theme]: {sorted(set(body_dark) - set(media_dark))}"
    )


def test_colour_classes_reference_defined_tokens() -> None:
    """Every var() a colour class reads resolves to a :root declaration."""
    css = _palette_css()
    root = _declarations(_block(css, _ROOT_BLOCK))
    referenced = set(_VAR_REFERENCE.findall(css))

    undefined = sorted(
        token
        for token in referenced
        if token not in root
        # The base bg/fg/border slots are set BY the colour classes
        # and consumed by the structural layer, not declared in :root.
        and token
        not in {
            "--gp-sphinx-badge-bg",
            "--gp-sphinx-badge-fg",
            "--gp-sphinx-badge-border",
        }
    )
    assert undefined == [], f"colour classes reference undefined tokens: {undefined}"


def test_root_token_families_have_dark_coverage() -> None:
    """Every light-mode token family has dark-mode declarations.

    Family-level, not token-level: ``state-deprecated`` legitimately
    declares a transparent ``-bg`` only in light mode, but its family
    still carries dark ``-fg``/``-border`` overrides. A family absent
    from the dark blocks entirely keeps light-mode colours in dark
    mode.
    """
    css = _palette_css()
    root_families = _families(_declarations(_block(css, _ROOT_BLOCK)))
    dark_families = _families(_declarations(_block(css, _MEDIA_DARK_BLOCK)))

    uncovered = sorted(root_families - dark_families)
    assert uncovered == [], f"token families without dark-mode coverage: {uncovered}"
