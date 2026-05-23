"""Unit tests for the option-parsing helpers in :mod:`sphinx_ux_grid._directives`."""

from __future__ import annotations

import typing as t

import pytest

from sphinx_ux_grid._directives import _columns_option, _gutter_to_length


class ColumnFixture(t.NamedTuple):
    """Test case for :func:`_columns_option`."""

    test_id: str
    argument: str
    expected: tuple[int, int, int, int]


_COLUMN_FIXTURES: list[ColumnFixture] = [
    ColumnFixture(test_id="single-int", argument="3", expected=(3, 3, 3, 3)),
    ColumnFixture(test_id="four-ints", argument="1 2 3 4", expected=(1, 2, 3, 4)),
    ColumnFixture(
        test_id="extra-whitespace", argument="  2   2  3 3 ", expected=(2, 2, 3, 3)
    ),
    ColumnFixture(test_id="min-bound", argument="1", expected=(1, 1, 1, 1)),
    ColumnFixture(test_id="max-bound", argument="12", expected=(12, 12, 12, 12)),
    ColumnFixture(test_id="mixed-range", argument="1 6 9 12", expected=(1, 6, 9, 12)),
]


@pytest.mark.parametrize(
    list(ColumnFixture._fields),
    _COLUMN_FIXTURES,
    ids=[f.test_id for f in _COLUMN_FIXTURES],
)
def test_columns_option_parses(
    test_id: str,
    argument: str,
    expected: tuple[int, int, int, int],
) -> None:
    """_columns_option returns four ints clamped to ``[1..12]``."""
    assert _columns_option(argument) == expected


class InvalidColumnFixture(t.NamedTuple):
    """Test case for invalid input to :func:`_columns_option`."""

    test_id: str
    argument: str | None


_INVALID_COLUMN_FIXTURES: list[InvalidColumnFixture] = [
    InvalidColumnFixture(test_id="none", argument=None),
    InvalidColumnFixture(test_id="empty", argument=""),
    InvalidColumnFixture(test_id="whitespace-only", argument="   "),
    InvalidColumnFixture(test_id="two-values", argument="1 2"),
    InvalidColumnFixture(test_id="three-values", argument="1 2 3"),
    InvalidColumnFixture(test_id="five-values", argument="1 2 3 4 5"),
    InvalidColumnFixture(test_id="below-min", argument="0"),
    InvalidColumnFixture(test_id="above-max", argument="13"),
    InvalidColumnFixture(test_id="non-int", argument="abc"),
    InvalidColumnFixture(test_id="mixed-bad", argument="1 2 3 abc"),
    InvalidColumnFixture(test_id="negative", argument="-1"),
]


@pytest.mark.parametrize(
    list(InvalidColumnFixture._fields),
    _INVALID_COLUMN_FIXTURES,
    ids=[f.test_id for f in _INVALID_COLUMN_FIXTURES],
)
def test_columns_option_rejects(test_id: str, argument: str | None) -> None:
    """_columns_option raises ValueError on malformed input."""
    with pytest.raises(ValueError):
        _columns_option(argument)


class GutterFixture(t.NamedTuple):
    """Test case for :func:`_gutter_to_length`."""

    test_id: str
    argument: str
    expected: str


_GUTTER_FIXTURES: list[GutterFixture] = [
    GutterFixture(test_id="scale-0", argument="0", expected="0"),
    GutterFixture(test_id="scale-1", argument="1", expected="0.25rem"),
    GutterFixture(test_id="scale-2", argument="2", expected="0.5rem"),
    GutterFixture(test_id="scale-3", argument="3", expected="1rem"),
    GutterFixture(test_id="scale-4", argument="4", expected="1.5rem"),
    GutterFixture(test_id="scale-5", argument="5", expected="3rem"),
    GutterFixture(test_id="css-rem", argument="2rem", expected="2rem"),
    GutterFixture(test_id="css-px", argument="16px", expected="16px"),
]


@pytest.mark.parametrize(
    list(GutterFixture._fields),
    _GUTTER_FIXTURES,
    ids=[f.test_id for f in _GUTTER_FIXTURES],
)
def test_gutter_to_length_maps(test_id: str, argument: str, expected: str) -> None:
    """_gutter_to_length maps 0..5 to a CSS scale and passes lengths through."""
    assert _gutter_to_length(argument) == expected


def test_gutter_to_length_takes_first_value() -> None:
    """Multiple gutter values collapse to the first (cross-breakpoint scale)."""
    assert _gutter_to_length("3 4") == "1rem"
