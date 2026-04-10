"""Tests for TYPE_CHECKING TypeAlias support in sphinx_autodoc_pytest_fixtures.

Feature: when a fixture's return type is a TypeAlias *defined* (not imported)
inside an ``if TYPE_CHECKING:`` block, ``_qualify_forward_ref`` should return
the fully-qualified name ``"{module}.{alias_name}"`` so Sphinx can build a
cross-reference to it.

TDD — these tests are written before the implementation.  Run::

    uv run pytest tests/ext/pytest_fixtures/test_type_checking_alias.py -v

to see all fail first; then implement the feature in _metadata.py.
"""

from __future__ import annotations

import sys
import textwrap
import types
import typing as t
from dataclasses import dataclass, field

import pytest

import sphinx_autodoc_pytest_fixtures._metadata as spf_meta
from sphinx_autodoc_pytest_fixtures._detection import _get_return_annotation
from sphinx_autodoc_pytest_fixtures._metadata import (
    _is_type_checking_guard,
    _qualify_forward_ref,
)
from sphinx_autodoc_pytest_fixtures._store import _get_spf_store

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fixture_fn(module_name: str) -> t.Any:
    """Return a minimal callable whose __module__ is *module_name*."""

    def _fn() -> None:
        pass

    _fn.__module__ = module_name
    return _fn


def _register_fake_module(
    name: str, source: str, monkeypatch: pytest.MonkeyPatch
) -> types.ModuleType:
    """Register a fake module and patch getsource to return *source*."""
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    monkeypatch.setattr(spf_meta.inspect, "getsource", lambda _: source)
    return mod


def _register_exec_module(
    name: str, source: str, monkeypatch: pytest.MonkeyPatch
) -> types.ModuleType:
    """Register a fake module, execute *source*, and patch getsource."""
    mod = types.ModuleType(name)
    mod.__file__ = f"<{name}>"
    sys.modules[name] = mod
    exec(compile(source, mod.__file__, "exec"), mod.__dict__)
    monkeypatch.setattr(spf_meta.inspect, "getsource", lambda _: source)
    return mod


@dataclass
class _FakeConfig:
    pytest_fixture_hidden_dependencies: frozenset[str] = field(
        default_factory=frozenset
    )
    pytest_fixture_builtin_links: dict[str, str] = field(default_factory=dict)
    pytest_external_fixture_links: dict[str, str] = field(default_factory=dict)


@dataclass
class _FakeApp:
    config: _FakeConfig = field(default_factory=_FakeConfig)


@dataclass
class _FakeEnv:
    domaindata: dict[str, t.Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Unit: _is_type_checking_guard (already working — sanity check)
# ---------------------------------------------------------------------------


def test_is_type_checking_guard_name_form() -> None:
    """TYPE_CHECKING as bare Name is recognised."""
    import ast

    node = ast.parse("if TYPE_CHECKING:\n    pass").body[0]
    assert isinstance(node, ast.If)
    assert _is_type_checking_guard(node)


def test_is_type_checking_guard_attr_form() -> None:
    """typing.TYPE_CHECKING / t.TYPE_CHECKING is recognised."""
    import ast

    node = ast.parse("if t.TYPE_CHECKING:\n    pass").body[0]
    assert isinstance(node, ast.If)
    assert _is_type_checking_guard(node)


def test_is_type_checking_guard_false_for_other_if() -> None:
    """Ordinary if-conditions are not mistaken for TYPE_CHECKING guards."""
    import ast

    node = ast.parse("if DEBUG:\n    pass").body[0]
    assert isinstance(node, ast.If)
    assert not _is_type_checking_guard(node)


# ---------------------------------------------------------------------------
# Unit: _qualify_forward_ref — existing behaviour (regression guard)
# ---------------------------------------------------------------------------


def test_qualify_forward_ref_import_from_type_checking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing behaviour: ImportFrom inside TYPE_CHECKING resolves correctly."""
    source = textwrap.dedent("""\
        from __future__ import annotations
        import typing as t
        if t.TYPE_CHECKING:
            from mod_b import Session
    """)
    mod_name = "fake_existing_mod"
    _register_fake_module(mod_name, source, monkeypatch)
    fn = _make_fixture_fn(mod_name)

    result = _qualify_forward_ref("Session", fn)
    assert result == "mod_b.Session"

    del sys.modules[mod_name]


def test_qualify_forward_ref_returns_none_for_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Names not present in TYPE_CHECKING block return None."""
    source = textwrap.dedent("""\
        from __future__ import annotations
        import typing as t
        if t.TYPE_CHECKING:
            from mod_b import Session
    """)
    mod_name = "fake_unknown_mod"
    _register_fake_module(mod_name, source, monkeypatch)
    fn = _make_fixture_fn(mod_name)

    result = _qualify_forward_ref("NonExistent", fn)
    assert result is None

    del sys.modules[mod_name]


# ---------------------------------------------------------------------------
# Unit: _qualify_forward_ref — NEW behaviour for TypeAlias inside TYPE_CHECKING
# ---------------------------------------------------------------------------


def test_qualify_forward_ref_typealias_in_type_checking_t_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TypeAlias defined in ``if t.TYPE_CHECKING:`` resolves to module.AliasName."""
    source = textwrap.dedent("""\
        from __future__ import annotations
        import typing as t
        import pytest
        from my_mod import MyBase

        if t.TYPE_CHECKING:
            from typing import TypeAlias
            MyAlias: TypeAlias = MyBase | None

        @pytest.fixture
        def my_fixture() -> MyAlias:
            return MyBase()
    """)
    mod_name = "fake_alias_t_mod"
    _register_fake_module(mod_name, source, monkeypatch)
    fn = _make_fixture_fn(mod_name)

    result = _qualify_forward_ref("MyAlias", fn)
    assert result == f"{mod_name}.MyAlias", (
        f"Expected '{mod_name}.MyAlias' but got {result!r}"
    )

    del sys.modules[mod_name]


def test_qualify_forward_ref_typealias_bare_type_checking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TypeAlias defined in ``if TYPE_CHECKING:`` (bare name) resolves correctly."""
    source = textwrap.dedent("""\
        from __future__ import annotations
        import typing
        import pytest
        from my_mod import MyBase

        if typing.TYPE_CHECKING:
            from typing import TypeAlias
            MyAlias: TypeAlias = MyBase | None
    """)
    mod_name = "fake_alias_bare_mod"
    _register_fake_module(mod_name, source, monkeypatch)
    fn = _make_fixture_fn(mod_name)

    result = _qualify_forward_ref("MyAlias", fn)
    assert result == f"{mod_name}.MyAlias"

    del sys.modules[mod_name]


def test_qualify_forward_ref_typealias_does_not_match_other_annassign(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AnnAssign that is NOT a TypeAlias (e.g. regular annotation) is ignored."""
    source = textwrap.dedent("""\
        from __future__ import annotations
        import typing as t

        if t.TYPE_CHECKING:
            count: int = 0          # plain annotation, not TypeAlias
    """)
    mod_name = "fake_non_alias_mod"
    _register_fake_module(mod_name, source, monkeypatch)
    fn = _make_fixture_fn(mod_name)

    result = _qualify_forward_ref("count", fn)
    # "count" is an AnnAssign but annotation is `int`, not `TypeAlias` → None
    assert result is None

    del sys.modules[mod_name]


def test_qualify_forward_ref_typealias_import_wins_over_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the same name is both imported and aliased in TYPE_CHECKING, import wins."""
    # Import is checked first in _qualify_forward_ref; the alias assignment
    # is a secondary resolution path.  Both name the same thing here but the
    # import should take priority.
    source = textwrap.dedent("""\
        from __future__ import annotations
        import typing as t

        if t.TYPE_CHECKING:
            from other_mod import MyAlias       # import
            from typing import TypeAlias
            MyAlias: TypeAlias = str | int      # also defined here (unusual)
    """)
    mod_name = "fake_import_priority_mod"
    _register_fake_module(mod_name, source, monkeypatch)
    fn = _make_fixture_fn(mod_name)

    result = _qualify_forward_ref("MyAlias", fn)
    # Import from other_mod wins
    assert result == "other_mod.MyAlias"

    del sys.modules[mod_name]


def test_qualify_forward_ref_typealias_t_dot_typealias_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``alias: t.TypeAlias = ...`` (attribute form) is also recognised."""
    source = textwrap.dedent("""\
        from __future__ import annotations
        import typing as t
        from base import Base

        if t.TYPE_CHECKING:
            Options: t.TypeAlias = Base | dict
    """)
    mod_name = "fake_attr_alias_mod"
    _register_fake_module(mod_name, source, monkeypatch)
    fn = _make_fixture_fn(mod_name)

    result = _qualify_forward_ref("Options", fn)
    assert result == f"{mod_name}.Options"

    del sys.modules[mod_name]


# ---------------------------------------------------------------------------
# Unit: _qualify_forward_ref — module-level TypeAlias (outside TYPE_CHECKING)
# ---------------------------------------------------------------------------


def test_qualify_forward_ref_fast_path_skips_typealias_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fast path must not use a TypeAlias value's __module__/__qualname__.

    When ``name`` is a TypeAlias at module scope, ``getattr(mod, name)``
    returns the alias *value* (e.g. a union type whose ``__qualname__``
    is ``"Union"``), not the alias itself.  Without guarding, the fast
    path would return ``"typing.Union"`` — which is wrong.
    """
    import types as _types

    mod_name = "fake_fast_path_alias_mod"
    mod = _types.ModuleType(mod_name)
    # Add the alias VALUE (a union type) as a runtime attribute, simulating
    # how ``MyAlias: TypeAlias = str | None`` is visible at runtime.
    mod.__dict__["MyAlias"] = str | None  # type: ignore[assignment]
    sys.modules[mod_name] = mod

    source = textwrap.dedent("""\
        from __future__ import annotations
        from typing import TypeAlias
        MyAlias: TypeAlias = str | None
    """)
    monkeypatch.setattr(spf_meta.inspect, "getsource", lambda _: source)
    fn = _make_fixture_fn(mod_name)

    result = _qualify_forward_ref("MyAlias", fn)
    assert result == f"{mod_name}.MyAlias", (
        f"Expected '{mod_name}.MyAlias' but got {result!r}. "
        "Fast path returned the alias value's module/qualname instead of the alias name."
    )

    del sys.modules[mod_name]


def test_qualify_forward_ref_module_level_typealias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TypeAlias defined at module level (not inside TYPE_CHECKING) is found.

    This covers the common pattern:

        MyAlias: TypeAlias = Base | None

    at the top of a module, which means ``_qualify_forward_ref`` must scan
    ``tree.body`` in addition to the TYPE_CHECKING block.
    """
    source = textwrap.dedent("""\
        from __future__ import annotations
        import typing as t
        from typing import TypeAlias
        from my_mod import MyBase

        MyAlias: TypeAlias = MyBase | None

        @t.overload
        def my_fixture() -> MyAlias: ...
    """)
    mod_name = "fake_module_level_alias_mod"
    _register_fake_module(mod_name, source, monkeypatch)
    fn = _make_fixture_fn(mod_name)

    result = _qualify_forward_ref("MyAlias", fn)
    assert result == f"{mod_name}.MyAlias", (
        f"Expected '{mod_name}.MyAlias' but got {result!r}. "
        "Module-level TypeAlias was not resolved."
    )

    del sys.modules[mod_name]


def test_qualify_forward_ref_module_level_t_typealias_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``alias: t.TypeAlias = ...`` at module level (attribute form) is recognised."""
    source = textwrap.dedent("""\
        from __future__ import annotations
        import typing as t
        from my_mod import Base

        MyOptions: t.TypeAlias = Base | dict
    """)
    mod_name = "fake_module_level_attr_alias_mod"
    _register_fake_module(mod_name, source, monkeypatch)
    fn = _make_fixture_fn(mod_name)

    result = _qualify_forward_ref("MyOptions", fn)
    assert result == f"{mod_name}.MyOptions"

    del sys.modules[mod_name]


def test_qualify_forward_ref_module_level_non_alias_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module-level AnnAssign that is NOT a TypeAlias is not returned."""
    source = textwrap.dedent("""\
        from __future__ import annotations
        count: int = 0
    """)
    mod_name = "fake_module_level_non_alias_mod"
    _register_fake_module(mod_name, source, monkeypatch)
    fn = _make_fixture_fn(mod_name)

    result = _qualify_forward_ref("count", fn)
    assert result is None

    del sys.modules[mod_name]


def test_qualify_forward_ref_type_checking_wins_over_module_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TYPE_CHECKING ImportFrom takes priority over a module-level alias of same name."""
    source = textwrap.dedent("""\
        from __future__ import annotations
        import typing as t
        from typing import TypeAlias
        from my_mod import MyBase

        MyAlias: TypeAlias = MyBase | None   # module-level alias

        if t.TYPE_CHECKING:
            from other_mod import MyAlias    # import takes priority
    """)
    mod_name = "fake_tc_priority_over_module_mod"
    _register_fake_module(mod_name, source, monkeypatch)
    fn = _make_fixture_fn(mod_name)

    result = _qualify_forward_ref("MyAlias", fn)
    # The TYPE_CHECKING ImportFrom should take priority
    assert result == "other_mod.MyAlias"

    del sys.modules[mod_name]


# ---------------------------------------------------------------------------
# Unit: _get_return_annotation — preserve bare-name alias annotation
# ---------------------------------------------------------------------------


def test_get_return_annotation_preserves_bare_identifier_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_get_return_annotation returns the raw string when annotation is a bare name.

    When a fixture is annotated with a TypeAlias name (e.g. ``-> MyAlias``)
    and ``from __future__ import annotations`` is active, the raw annotation
    is the string ``"MyAlias"``.  ``get_type_hints()`` would expand this to the
    actual union type — losing the alias name.  The function should return
    ``"MyAlias"`` directly so that _qualify_forward_ref can qualify it later.
    """
    import types

    # Build a real module so get_type_hints can see it
    mod_source = textwrap.dedent("""\
        from __future__ import annotations
        import typing as t
        from typing import TypeAlias
        from collections.abc import Mapping

        class MyBase:
            pass

        MyAlias: TypeAlias = MyBase | None
    """)
    mod_name = "fake_get_ret_ann_alias_mod"
    mod = types.ModuleType(mod_name)
    exec(compile(mod_source, "<string>", "exec"), mod.__dict__)
    import sys

    sys.modules[mod_name] = mod

    # Build a fixture function annotated with the alias name
    # Must be defined in the same module namespace so get_type_hints works
    fn_source = textwrap.dedent("""\
        from __future__ import annotations
        import pytest

        @pytest.fixture
        def my_fixture() -> MyAlias:
            return MyBase()
    """)
    exec(compile(fn_source, "<string>", "exec"), mod.__dict__)
    fixture_obj = mod.__dict__["my_fixture"]

    ann = _get_return_annotation(fixture_obj)
    assert ann == "MyAlias", (
        f"Expected raw string 'MyAlias' but got {ann!r}. "
        "_get_return_annotation expanded the alias instead of preserving the name."
    )

    del sys.modules[mod_name]


def test_get_return_annotation_class_import_alias_resolves_to_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_get_return_annotation resolves import-aliased classes to the actual class.

    When a fixture has ``from mod import Cls as Alias`` at module level and
    annotates ``-> Alias``, ``get_type_hints()`` resolves the string to the
    real class.  The function must return the class (not the raw string
    ``"Alias"``) so Sphinx can link to the class documentation.
    """
    import types

    mod_source = textwrap.dedent("""\
        from __future__ import annotations
        import pytest

        class RealClass:
            pass

        # Import alias pattern: annotate with the alias name
        AliasForClass = RealClass
    """)
    mod_name = "fake_import_alias_mod"
    mod = types.ModuleType(mod_name)
    exec(compile(mod_source, "<string>", "exec"), mod.__dict__)
    import sys

    sys.modules[mod_name] = mod

    fn_source = textwrap.dedent("""\
        from __future__ import annotations
        import pytest

        @pytest.fixture
        def my_fixture() -> AliasForClass:
            return RealClass()
    """)
    exec(compile(fn_source, "<string>", "exec"), mod.__dict__)
    fixture_obj = mod.__dict__["my_fixture"]

    ann = _get_return_annotation(fixture_obj)
    # Should return the class object, not the raw string "AliasForClass"
    RealClass = mod.__dict__["RealClass"]
    assert ann is RealClass, (
        f"Expected RealClass but got {ann!r}. "
        "_get_return_annotation should resolve import-aliased class names."
    )

    del sys.modules[mod_name]


# ---------------------------------------------------------------------------
# Registration: meta.return_display is qualified for TYPE_CHECKING alias return
# ---------------------------------------------------------------------------


def test_type_checking_alias_qualified_in_fixture_meta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registration qualifies TYPE_CHECKING aliases without a Sphinx build.

    The fixture module defines ``MyAlias: TypeAlias = MyBase | None`` inside
    ``if t.TYPE_CHECKING:``. After registration, ``meta.return_display`` should
    be ``"fixture_mod.MyAlias"`` (qualified) rather than bare ``"MyAlias"``.
    """

    fixture_source = textwrap.dedent("""\
        from __future__ import annotations
        import typing as t
        import pytest

        class MyBase:
            \"\"\"A base class.\"\"\"

        if t.TYPE_CHECKING:
            from typing import TypeAlias
            MyAlias: TypeAlias = MyBase | None

        @pytest.fixture
        def my_fixture() -> MyAlias:
            \"\"\"Return a MyAlias instance.\"\"\"
            return MyBase()
    """)
    module_name = "fixture_mod"
    module = _register_exec_module(module_name, fixture_source, monkeypatch)
    fixture_obj = module.__dict__["my_fixture"]
    env = _FakeEnv()
    app = _FakeApp()

    try:
        meta = spf_meta._register_fixture_meta(
            env=env,
            docname="index",
            obj=fixture_obj,
            public_name="my_fixture",
            source_name="my_fixture",
            modname=module_name,
            kind="",
            app=app,
        )
    finally:
        sys.modules.pop(module_name, None)

    store = _get_spf_store(env)
    assert meta.return_display == "fixture_mod.MyAlias", (
        f"Expected 'fixture_mod.MyAlias' but got {meta.return_display!r}. "
        "TYPE_CHECKING TypeAlias was not qualified — check _qualify_forward_ref."
    )
    assert store["fixtures"]["fixture_mod.my_fixture"] == meta
    assert store["public_to_canon"]["my_fixture"] == "fixture_mod.my_fixture"
