"""Render coverage for every bundled icon."""

from __future__ import annotations

import typing as t

import pytest

from sphinx_ux_octicons._render import load_octicons, render_octicon


class IconFixture(t.NamedTuple):
    """One curated icon name."""

    test_id: str
    name: str


_BUNDLED: list[IconFixture] = [
    IconFixture(test_id=name, name=name) for name in sorted(load_octicons())
]


def test_bundled_icon_count() -> None:
    """All 18 curated icons land in the bundled JSON."""
    assert len(_BUNDLED) == 18


@pytest.mark.parametrize(
    list(IconFixture._fields),
    _BUNDLED,
    ids=[f.test_id for f in _BUNDLED],
)
def test_render_icon_emits_payload_and_class(test_id: str, name: str) -> None:
    """render_octicon embeds the icon's path payload and namespace class."""
    svg = render_octicon(name)
    entry = load_octicons()[name]
    assert svg.startswith("<svg ")
    assert svg.endswith("</svg>")
    assert entry["path"] in svg
    expected_class = f'class="gp-sphinx-octicon gp-sphinx-octicon--{name}"'
    assert expected_class in svg
