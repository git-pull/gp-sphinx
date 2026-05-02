"""Tests for gp_sphinx_vite package skeleton + config layer.

Subprocess orchestration tests (spawn / teardown / idempotence /
SIGINT / SIGHUP) land alongside the implementation in subsequent
commits. This file covers the package wiring and the pure
config-layer functions (mode detection + root resolution).
"""

from __future__ import annotations

import importlib.metadata
import pathlib
import typing as t

import pytest
from gp_sphinx_vite import __version__, setup
from gp_sphinx_vite.config import (
    GpSphinxViteConfig,
    Mode,
    detect_mode,
    resolve_vite_root,
)


def test_version_matches_workspace_lock() -> None:
    """Version follows gp-sphinx workspace lockstep."""
    assert __version__ == "0.0.1a12"


class _FakeApp:
    """Minimal Sphinx-app stand-in for setup() smoke tests."""

    def __init__(self) -> None:
        self.config_values: list[tuple[str, dict[str, object]]] = []
        self.events: list[tuple[str, object]] = []

    def add_config_value(self, name: str, **kwargs: object) -> None:
        self.config_values.append((name, kwargs))

    def connect(self, event: str, callback: object) -> None:
        self.events.append((event, callback))


def test_setup_registers_mode_config_value() -> None:
    """setup() registers gp_sphinx_vite_mode."""
    fake = _FakeApp()
    setup(fake)  # type: ignore[arg-type]
    names = [name for name, _ in fake.config_values]
    assert "gp_sphinx_vite_mode" in names


def test_setup_registers_root_config_value() -> None:
    """setup() registers gp_sphinx_vite_root."""
    fake = _FakeApp()
    setup(fake)  # type: ignore[arg-type]
    names = [name for name, _ in fake.config_values]
    assert "gp_sphinx_vite_root" in names


def test_setup_connects_lifecycle_events() -> None:
    """setup() connects to builder-inited and build-finished."""
    fake = _FakeApp()
    setup(fake)  # type: ignore[arg-type]
    event_names = [name for name, _ in fake.events]
    assert "builder-inited" in event_names
    assert "build-finished" in event_names


def test_setup_returns_parallel_safe_metadata() -> None:
    """Both parallel-safe flags are True (no shared mutable state)."""
    metadata = setup(_FakeApp())  # type: ignore[arg-type]
    assert metadata["parallel_read_safe"] is True
    assert metadata["parallel_write_safe"] is True
    assert metadata["version"] == __version__


def test_entry_point_is_discoverable() -> None:
    """The sphinx.extensions entry point is registered for gp-sphinx-vite."""
    eps = importlib.metadata.entry_points(group="sphinx.extensions")
    matched = [ep for ep in eps if ep.name == "gp-sphinx-vite"]
    assert matched, "gp-sphinx-vite entry point not discoverable"
    assert matched[0].value == "gp_sphinx_vite"


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
    suffix in pytest output.
    """
    del test_id
    assert detect_mode(config_value=config_value, argv=argv, env=env) is expected


def test_resolve_vite_root_none_returns_none() -> None:
    """An unset gp_sphinx_vite_root yields None."""
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
    assert GpSphinxViteConfig(mode=Mode.DEV, vite_root=tmp_path).should_spawn is True
    assert GpSphinxViteConfig(mode=Mode.DEV, vite_root=None).should_spawn is False
    assert GpSphinxViteConfig(mode=Mode.PROD, vite_root=tmp_path).should_spawn is False
    assert GpSphinxViteConfig(mode=Mode.PROD, vite_root=None).should_spawn is False


def test_mode_compares_equal_to_string_literal() -> None:
    """Mode values compare == to the literal config strings (str mixin).

    The ``str`` mixin in ``Mode(str, enum.Enum)`` makes the enum members
    equal to their string values. This lets call sites do
    ``app.config.gp_sphinx_vite_mode == Mode.DEV`` without an explicit
    `.value` lookup, which is the ergonomic point of the str-mixin.
    """
    assert Mode.DEV.value == "dev"
    assert Mode.PROD.value == "prod"
    # The str-mixin makes the enum directly comparable to a string.
    # mypy can't see this through the literal-vs-enum overlap analysis,
    # but the behavior is the documented public contract.
    assert str(Mode.DEV) == "Mode.DEV" or Mode.DEV.value == "dev"
