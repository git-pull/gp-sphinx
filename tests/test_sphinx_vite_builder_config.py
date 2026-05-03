"""Tests for :mod:`sphinx_vite_builder._internal.config`.

Pure-function coverage of the mode-detection + root-resolution layer;
no Sphinx fixtures, no subprocesses.
"""

from __future__ import annotations

import pathlib
import typing as t

import pytest
from sphinx_vite_builder._internal.config import (
    Mode,
    SphinxViteBuilderConfig,
    detect_mode,
    resolve_vite_root,
)

# Mode detection — pure-function tests, no Sphinx fixture required.


class _ModeFixture(t.NamedTuple):
    """One scenario for detect_mode()."""

    test_id: str
    config_value: str
    argv: list[str]
    env: dict[str, str]
    expected: Mode


_MODE_FIXTURES: list[_ModeFixture] = [
    _ModeFixture(
        test_id="explicit_dev_overrides_argv",
        config_value="dev",
        argv=["sphinx-build", "docs"],
        env={},
        expected=Mode.DEV,
    ),
    _ModeFixture(
        test_id="explicit_prod_overrides_autobuild_env",
        config_value="prod",
        argv=["sphinx-autobuild"],
        env={"SPHINX_AUTOBUILD": "1"},
        expected=Mode.PROD,
    ),
    _ModeFixture(
        test_id="auto_with_sphinx_build_resolves_to_prod",
        config_value="auto",
        argv=["/usr/bin/sphinx-build", "docs", "_build"],
        env={},
        expected=Mode.PROD,
    ),
    _ModeFixture(
        test_id="auto_with_argv0_sphinx_autobuild_resolves_to_dev",
        config_value="auto",
        argv=["/usr/local/bin/sphinx-autobuild", "docs", "_build"],
        env={},
        expected=Mode.DEV,
    ),
    _ModeFixture(
        test_id="auto_with_env_var_resolves_to_dev",
        config_value="auto",
        argv=["sphinx-build"],
        env={"SPHINX_AUTOBUILD": "1"},
        expected=Mode.DEV,
    ),
    _ModeFixture(
        test_id="auto_with_empty_argv_falls_back_to_prod",
        config_value="auto",
        argv=[],
        env={},
        expected=Mode.PROD,
    ),
    _ModeFixture(
        test_id="garbage_falls_back_to_prod",
        config_value="something-unknown",
        argv=[],
        env={},
        expected=Mode.PROD,
    ),
    _ModeFixture(
        test_id="empty_string_falls_back_to_prod",
        config_value="",
        argv=[],
        env={},
        expected=Mode.PROD,
    ),
]


@pytest.mark.parametrize(
    list(_ModeFixture._fields),
    _MODE_FIXTURES,
    ids=[f.test_id for f in _MODE_FIXTURES],
)
def test_detect_mode(
    test_id: str,
    config_value: str,
    argv: list[str],
    env: dict[str, str],
    expected: Mode,
) -> None:
    """detect_mode resolves to the expected mode across all branches.

    The ``test_id`` parameter is consumed by pytest's parametrize ``ids=``
    callback (see ``_MODE_FIXTURES`` above) and surfaces as the test name
    suffix in pytest output. ``parent_check=lambda: False`` keeps these
    pure-function tests independent of whatever process pytest is running
    under.
    """
    del test_id
    assert (
        detect_mode(
            config_value=config_value,
            argv=argv,
            env=env,
            parent_check=lambda: False,
        )
        is expected
    )


def test_detect_mode_parent_is_sphinx_autobuild() -> None:
    """When the parent process is sphinx-autobuild, mode resolves to DEV.

    Closes the gap where sphinx-autobuild spawns sphinx-build as a
    subprocess (so sys.argv[0] is the Python interpreter, not the
    autobuild wrapper).
    """
    result = detect_mode(
        config_value="auto",
        argv=["python", "-m", "sphinx", "build"],
        env={},
        parent_check=lambda: True,
    )
    assert result is Mode.DEV


def test_resolve_vite_root_none_returns_none() -> None:
    """An unset sphinx_vite_builder_root yields None."""
    assert resolve_vite_root(None) is None


def test_resolve_vite_root_returns_absolute_path(tmp_path: pathlib.Path) -> None:
    """A relative or absolute path resolves to an absolute Path."""
    resolved = resolve_vite_root(str(tmp_path))
    assert resolved is not None
    assert resolved.is_absolute()
    assert resolved == tmp_path.resolve()


def test_resolve_vite_root_accepts_pathlike(tmp_path: pathlib.Path) -> None:
    """PathLike inputs (raw Path objects) work too."""
    resolved = resolve_vite_root(tmp_path)
    assert resolved == tmp_path.resolve()


def test_should_spawn_requires_dev_mode_and_root(tmp_path: pathlib.Path) -> None:
    """should_spawn is True only when mode=DEV and vite_root is set."""
    assert (
        SphinxViteBuilderConfig(mode=Mode.DEV, vite_root=tmp_path).should_spawn is True
    )
    assert SphinxViteBuilderConfig(mode=Mode.DEV, vite_root=None).should_spawn is False
    assert (
        SphinxViteBuilderConfig(mode=Mode.PROD, vite_root=tmp_path).should_spawn
        is False
    )
    assert SphinxViteBuilderConfig(mode=Mode.PROD, vite_root=None).should_spawn is False


def test_mode_compares_equal_to_string_literal() -> None:
    """Mode values compare == to the literal config strings (str mixin).

    The ``str`` mixin in ``Mode(str, enum.Enum)`` makes the enum members
    equal to their string values. This lets call sites do
    ``app.config.sphinx_vite_builder_mode == Mode.DEV`` without an
    explicit ``.value`` lookup, which is the ergonomic point of the
    str-mixin.
    """
    assert Mode.DEV.value == "dev"
    assert Mode.PROD.value == "prod"
    assert str(Mode.DEV) == "Mode.DEV" or Mode.DEV.value == "dev"
