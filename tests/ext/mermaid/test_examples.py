"""The committed example diagrams stay paired with their rendered SVGs."""

from __future__ import annotations

import pathlib
import re
import typing as t

import pytest

import sphinx_gp_mermaid as sgm

_EXAMPLES_DIR = pathlib.Path(sgm.__file__).resolve().parents[2] / "examples"
_SRC_DIR = _EXAMPLES_DIR / "src"
_RENDERED_DIR = _EXAMPLES_DIR / "rendered"

_SVG_ID_RE = re.compile(r'id="mermaid-[0-9a-f]{12}-(?:light|dark)"')


class ExampleCase(t.NamedTuple):
    """One example source and the stem its rendered SVGs share."""

    test_id: str
    source: pathlib.Path


_EXAMPLE_CASES: list[ExampleCase] = [
    ExampleCase(test_id=path.stem, source=path)
    for path in sorted(_SRC_DIR.glob("*.mmd"))
]


def test_examples_dir_is_populated() -> None:
    """The gallery ships a diverse set of sources (guards an empty glob)."""
    assert len(_EXAMPLE_CASES) >= 10


@pytest.mark.parametrize(
    "case",
    _EXAMPLE_CASES,
    ids=[c.test_id for c in _EXAMPLE_CASES],
)
def test_example_has_dual_theme_outputs(case: ExampleCase) -> None:
    """Each source has a committed light and dark SVG from the real pipeline."""
    light = _RENDERED_DIR / f"{case.test_id}.light.svg"
    dark = _RENDERED_DIR / f"{case.test_id}.dark.svg"
    assert light.is_file(), f"{case.test_id}: missing {light.name}"
    assert dark.is_file(), f"{case.test_id}: missing {dark.name}"

    light_text = light.read_text(encoding="utf-8")
    dark_text = dark.read_text(encoding="utf-8")
    assert light_text.startswith("<svg "), f"{case.test_id}: light not an SVG"
    assert dark_text.startswith("<svg "), f"{case.test_id}: dark not an SVG"
    assert 'id="mermaid-' in light_text and "-light" in light_text
    assert 'id="mermaid-' in dark_text and "-dark" in dark_text
    assert _SVG_ID_RE.search(light_text), f"{case.test_id}: light id not normalized"
    assert _SVG_ID_RE.search(dark_text), f"{case.test_id}: dark id not normalized"
    assert light_text != dark_text, f"{case.test_id}: variants are identical"
