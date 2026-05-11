"""Unit tests for sphinx_autodoc_typehints_gp._param_defaults."""

from __future__ import annotations

import dataclasses
import inspect
import typing as t

import pytest
from sphinx.util.inspect import DefaultValue

from sphinx_autodoc_typehints_gp._param_defaults import (
    _walk_to_dataclass,
    update_synthetic_defvalues,
)
from sphinx_autodoc_typehints_gp._resolvers import (
    DataclassFactoryRepr,
    ResolveContext,
)

# ---------------------------------------------------------------------------
# DataclassFactoryRepr
# ---------------------------------------------------------------------------


class _FactoryFixture(t.NamedTuple):
    test_id: str
    factory: object
    expected: str | None


def _ctx(value: object) -> ResolveContext:
    return ResolveContext(
        value=value,
        kind="param",
        qualname="Foo.__init__",
        param_name="x",
        default_repr="<factory>",
    )


_FACTORY_FIXTURES: list[_FactoryFixture] = [
    _FactoryFixture("list", list, "[]"),
    _FactoryFixture("dict", dict, "{}"),
    _FactoryFixture("set", set, "set()"),
    _FactoryFixture("frozenset", frozenset, "frozenset()"),
    _FactoryFixture("tuple", tuple, "()"),
    _FactoryFixture("named_class", _FactoryFixture, "_FactoryFixture()"),
    _FactoryFixture("lambda", lambda: 1, None),
    _FactoryFixture("function", _ctx, None),
]


@pytest.mark.parametrize(
    list(_FactoryFixture._fields),
    _FACTORY_FIXTURES,
    ids=[f.test_id for f in _FACTORY_FIXTURES],
)
def test_dataclass_factory_repr_resolves_each_shape(
    test_id: str,
    factory: object,
    expected: str | None,
) -> None:
    """DataclassFactoryRepr returns the expected text per factory shape."""
    del test_id
    assert DataclassFactoryRepr()(_ctx(factory)) == expected


def test_dataclass_factory_repr_defers_for_non_param_kind() -> None:
    """A 'data' / 'attribute' context is not handled by this resolver."""
    ctx = ResolveContext(
        value=list,
        kind="data",
        qualname="mod.SOME_LIST",
        param_name=None,
        default_repr="[]",
    )
    assert DataclassFactoryRepr()(ctx) is None


# ---------------------------------------------------------------------------
# _walk_to_dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _ProbeDataclass:
    x: list[int] = dataclasses.field(default_factory=list)
    y: dict[str, int] = dataclasses.field(default_factory=dict)
    z: int = 5


class _PlainClass:
    def __init__(self, x: int = 0) -> None:
        self.x = x


def test_walk_to_dataclass_returns_class_when_passed_class() -> None:
    """Passing the dataclass itself returns it."""
    assert _walk_to_dataclass(_ProbeDataclass) is _ProbeDataclass


def test_walk_to_dataclass_returns_class_for_init_method() -> None:
    """Passing the __init__ resolves to the owning dataclass."""
    assert _walk_to_dataclass(_ProbeDataclass.__init__) is _ProbeDataclass


def test_walk_to_dataclass_returns_none_for_non_dataclass() -> None:
    """A regular class is not a dataclass; returns None."""
    assert _walk_to_dataclass(_PlainClass) is None
    assert _walk_to_dataclass(_PlainClass.__init__) is None


def test_walk_to_dataclass_returns_none_for_arbitrary_function() -> None:
    """A free function is not a dataclass init."""

    def some_function() -> None:
        return None

    assert _walk_to_dataclass(some_function) is None


# ---------------------------------------------------------------------------
# update_synthetic_defvalues
# ---------------------------------------------------------------------------


class _FakeConfig:
    gp_typehints_curate_param_defaults: bool = True


class _FakeApp:
    def __init__(self, *, enabled: bool = True) -> None:
        self.config = _FakeConfig()
        self.config.gp_typehints_curate_param_defaults = enabled


def test_update_synthetic_defvalues_wraps_factory_defaults_in_shim() -> None:
    """A dataclass with default_factory fields gets DefaultValue shims."""
    app = t.cast("t.Any", _FakeApp())

    @dataclasses.dataclass
    class _Local:
        items: list[int] = dataclasses.field(default_factory=list)
        mapping: dict[str, int] = dataclasses.field(default_factory=dict)

    update_synthetic_defvalues(app, _Local, bound_method=False)
    sig = inspect.signature(_Local)
    items_default = sig.parameters["items"].default
    mapping_default = sig.parameters["mapping"].default
    assert isinstance(items_default, DefaultValue)
    assert repr(items_default) == "[]"
    assert isinstance(mapping_default, DefaultValue)
    assert repr(mapping_default) == "{}"


def test_update_synthetic_defvalues_leaves_direct_value_defaults_alone() -> None:
    """Fields with `default=` (not factory) are not modified."""
    app = t.cast("t.Any", _FakeApp())

    @dataclasses.dataclass
    class _Local:
        items: list[int] = dataclasses.field(default_factory=list)
        count: int = 5

    update_synthetic_defvalues(app, _Local, bound_method=False)
    sig = inspect.signature(_Local)
    # count has direct default; should remain int 5
    assert sig.parameters["count"].default == 5
    assert not isinstance(sig.parameters["count"].default, DefaultValue)


def test_update_synthetic_defvalues_skips_when_flag_disabled() -> None:
    """Setting gp_typehints_curate_param_defaults=False is a hard kill-switch."""
    app = t.cast("t.Any", _FakeApp(enabled=False))

    @dataclasses.dataclass
    class _Local:
        items: list[int] = dataclasses.field(default_factory=list)

    update_synthetic_defvalues(app, _Local, bound_method=False)
    sig = inspect.signature(_Local)
    assert not isinstance(sig.parameters["items"].default, DefaultValue)


def test_update_synthetic_defvalues_skips_non_dataclass() -> None:
    """A regular class's __init__ is untouched."""
    app = t.cast("t.Any", _FakeApp())

    class _Plain:
        def __init__(self, x: int = 0) -> None:
            self.x = x

    update_synthetic_defvalues(app, _Plain, bound_method=False)
    sig = inspect.signature(_Plain)
    assert sig.parameters["x"].default == 0
    assert not isinstance(sig.parameters["x"].default, DefaultValue)


def test_update_synthetic_defvalues_idempotent_with_existing_shim() -> None:
    """Pre-existing DefaultValue shims (from Sphinx update_defvalue) survive."""
    app = t.cast("t.Any", _FakeApp())

    @dataclasses.dataclass
    class _Local:
        items: list[int] = dataclasses.field(default_factory=list)

    update_synthetic_defvalues(app, _Local, bound_method=False)
    first = inspect.signature(_Local).parameters["items"].default
    update_synthetic_defvalues(app, _Local, bound_method=False)
    second = inspect.signature(_Local).parameters["items"].default
    assert isinstance(first, DefaultValue)
    assert isinstance(second, DefaultValue)
    assert repr(first) == repr(second) == "[]"
