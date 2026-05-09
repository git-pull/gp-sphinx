"""Unit tests for sphinx_autodoc_typehints_gp._data_defaults."""

from __future__ import annotations

import typing as t

import pytest

from sphinx_autodoc_typehints_gp._data_defaults import (
    TruncateLongRepr,
    _curate_value_line,
)
from sphinx_autodoc_typehints_gp._param_defaults import ResolveContext


def _ctx(default_repr: str, kind: str = "data") -> ResolveContext:
    return ResolveContext(
        value=None,
        kind=kind,
        qualname="mod.X",
        param_name=None,
        default_repr=default_repr,
    )


# ---------------------------------------------------------------------------
# TruncateLongRepr
# ---------------------------------------------------------------------------


class _TruncateFixture(t.NamedTuple):
    test_id: str
    default_repr: str
    threshold: int
    expected: str | None


_TRUNCATE_FIXTURES: list[_TruncateFixture] = [
    _TruncateFixture("short", "[1, 2]", 10, None),
    _TruncateFixture("at_threshold", "0123456789", 10, None),
    _TruncateFixture("over_threshold", "x" * 50, 10, "<...truncated, 50 chars>"),
    _TruncateFixture("empty", "", 10, None),
]


@pytest.mark.parametrize(
    list(_TruncateFixture._fields),
    _TRUNCATE_FIXTURES,
    ids=[f.test_id for f in _TRUNCATE_FIXTURES],
)
def test_truncate_long_repr_decides_per_length(
    test_id: str,
    default_repr: str,
    threshold: int,
    expected: str | None,
) -> None:
    """TruncateLongRepr returns the truncated marker only above threshold."""
    del test_id
    assert TruncateLongRepr(threshold=threshold)(_ctx(default_repr)) == expected


def test_truncate_long_repr_defers_for_param_kind() -> None:
    """TruncateLongRepr is for data/attribute only; param contexts defer."""
    long_text = "x" * 500
    assert TruncateLongRepr(threshold=200)(_ctx(long_text, kind="param")) is None


# ---------------------------------------------------------------------------
# _curate_value_line
# ---------------------------------------------------------------------------


class _FakeConfig:
    gp_typehints_curate_data_defaults: bool = True


class _FakeDocumenter:
    """Minimal stand-in for DataDocumenter / AttributeDocumenter."""

    def __init__(self, *, value: object, fullname: str, objtype: str = "data") -> None:
        self.object = value
        self.fullname = fullname
        self.objtype = objtype
        self.config = _FakeConfig()


def test_curate_value_line_passes_through_non_value_lines() -> None:
    """Lines that aren't `:value: …` are not touched."""
    documenter = t.cast("t.Any", _FakeDocumenter(value=None, fullname="mod.X"))
    assert _curate_value_line(documenter, "   :type: int") is None


def test_curate_value_line_keeps_short_values() -> None:
    """Short values fall through the resolver chain (returns None)."""
    documenter = t.cast("t.Any", _FakeDocumenter(value=None, fullname="mod.X"))
    assert _curate_value_line(documenter, "   :value: 42") is None


def test_curate_value_line_truncates_long_values() -> None:
    """Long values are replaced with a truncated marker."""
    long_text = "[1, 2, 3" + ", 4" * 200 + "]"
    documenter = t.cast("t.Any", _FakeDocumenter(value=None, fullname="mod.X"))
    line = f"   :value: {long_text}"
    result = _curate_value_line(documenter, line)
    assert result is not None
    assert result.startswith("   :value: <...truncated,")
    assert result.endswith(" chars>")


def test_curate_value_line_skipped_when_flag_disabled() -> None:
    """Setting the kill-switch makes the curator a no-op for value lines."""
    long_text = "x" * 500
    documenter = t.cast("t.Any", _FakeDocumenter(value=None, fullname="mod.X"))
    documenter.config.gp_typehints_curate_data_defaults = False
    assert _curate_value_line(documenter, f"   :value: {long_text}") is None
