"""Height-parse and lookup error coverage for ``render_octicon``."""

from __future__ import annotations

import typing as t

import pytest

from sphinx_ux_octicons._render import load_octicons, render_octicon


class HeightFixture(t.NamedTuple):
    """One height-parse case."""

    test_id: str
    height: str
    expected_width: str
    expected_height: str


_VALID: list[HeightFixture] = [
    HeightFixture(
        test_id="em-default",
        height="1em",
        expected_width='width="1.0em"',
        expected_height='height="1.0em"',
    ),
    HeightFixture(
        test_id="px-24",
        height="24px",
        expected_width='width="24.0px"',
        expected_height='height="24.0px"',
    ),
    HeightFixture(
        test_id="rem-fractional",
        height="1.5rem",
        expected_width='width="1.5rem"',
        expected_height='height="1.5rem"',
    ),
]


@pytest.mark.parametrize(
    list(HeightFixture._fields),
    _VALID,
    ids=[f.test_id for f in _VALID],
)
def test_render_valid_height_units(
    test_id: str,
    height: str,
    expected_width: str,
    expected_height: str,
) -> None:
    """Valid CSS lengths render width/height with the same unit and a 1:1 ratio."""
    # The bundled 16x16 icons keep a square aspect ratio, so width == height.
    svg = render_octicon("rocket", height=height)
    assert expected_width in svg
    assert expected_height in svg


def test_render_aspect_ratio_preserved() -> None:
    """Width tracks ``original_width * value / original_height`` exactly."""
    # rocket is 16x16; scaling height to 32px should yield width 32px too.
    svg = render_octicon("rocket", height="32px")
    assert 'width="32.0px"' in svg
    assert 'height="32.0px"' in svg


def test_render_rejects_unitless_height() -> None:
    """Heights without a CSS unit raise ``ValueError``."""
    with pytest.raises(ValueError, match="invalid height"):
        render_octicon("rocket", height="1")


def test_render_rejects_unknown_unit() -> None:
    """Unsupported units raise ``ValueError``."""
    with pytest.raises(ValueError, match="invalid height"):
        render_octicon("rocket", height="2pt")


def test_render_rejects_unknown_icon() -> None:
    """Unknown icon names raise ``KeyError`` with the requested name."""
    with pytest.raises(KeyError) as excinfo:
        render_octicon("not-a-real-icon")
    assert excinfo.value.args == ("not-a-real-icon",)


def test_render_appends_extra_classes() -> None:
    """Extra classes are appended after the namespace pair."""
    svg = render_octicon("rocket", classes=("extra-one", "extra-two"))
    assert (
        'class="gp-sphinx-octicon gp-sphinx-octicon--rocket extra-one extra-two"' in svg
    )


def test_load_octicons_is_cached() -> None:
    """``load_octicons`` returns the same mapping on repeated calls."""
    assert load_octicons() is load_octicons()
