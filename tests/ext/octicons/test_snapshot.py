"""Snapshot coverage of ``render_octicon`` for every bundled icon."""

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


@pytest.mark.parametrize(
    list(IconFixture._fields),
    _BUNDLED,
    ids=[f.test_id for f in _BUNDLED],
)
def test_render_snapshot(
    test_id: str,
    name: str,
    snapshot_html_fragment: t.Callable[..., None],
) -> None:
    """Each bundled icon renders to a stable SVG fragment."""
    snapshot_html_fragment(render_octicon(name), name=name)
