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

import pytest

import sphinx_autodoc_pytest_fixtures._metadata as spf_meta
from sphinx_autodoc_pytest_fixtures._metadata import (
    _is_type_checking_guard,
    _qualify_forward_ref,
)

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
# Integration: meta.return_display is qualified for TYPE_CHECKING alias return
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_type_checking_alias_qualified_in_fixture_meta(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Fixture with TYPE_CHECKING TypeAlias return gets qualified return_display.

    The fixture module defines ``MyAlias: TypeAlias = MyBase | None`` inside
    ``if t.TYPE_CHECKING:``.  After the build, ``meta.return_display`` should
    be ``"fixture_mod.MyAlias"`` (qualified) rather than bare ``"MyAlias"``.
    """
    import io
    import sys

    from sphinx.application import Sphinx

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

    index_rst = textwrap.dedent("""\
        Test
        ====

        .. py:module:: fixture_mod

        .. autofixture-index:: fixture_mod

        .. autofixture:: fixture_mod.my_fixture
    """)

    srcdir = tmp_path / "src"  # type: ignore[operator]
    outdir = tmp_path / "out"  # type: ignore[operator]
    doctreedir = tmp_path / ".doctrees"  # type: ignore[operator]
    srcdir.mkdir()
    outdir.mkdir()
    doctreedir.mkdir()

    (srcdir / "fixture_mod.py").write_text(fixture_source, encoding="utf-8")
    conf_py = textwrap.dedent(f"""\
        import sys
        sys.path.insert(0, "{srcdir}")
        extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_pytest_fixtures"]
        master_doc = "index"
        exclude_patterns = ["_build"]
        html_theme = "alabaster"
    """)
    (srcdir / "conf.py").write_text(conf_py, encoding="utf-8")
    (srcdir / "index.rst").write_text(index_rst, encoding="utf-8")

    for key in list(sys.modules):
        if key == "fixture_mod" or key.startswith("fixture_mod."):
            del sys.modules[key]

    app = Sphinx(
        srcdir=str(srcdir),
        confdir=str(srcdir),
        outdir=str(outdir),
        doctreedir=str(doctreedir),
        buildername="html",
        confoverrides={"pytest_fixture_lint_level": "none"},
        status=io.StringIO(),
        warning=io.StringIO(),
        freshenv=True,
    )
    app.build()

    store = app.env.domaindata.get("sphinx_autodoc_pytest_fixtures", {})
    meta = store["fixtures"].get("fixture_mod.my_fixture")
    assert meta is not None, "fixture_mod.my_fixture not found in store"
    assert meta.return_display == "fixture_mod.MyAlias", (
        f"Expected 'fixture_mod.MyAlias' but got {meta.return_display!r}. "
        "TYPE_CHECKING TypeAlias was not qualified — check _qualify_forward_ref."
    )
