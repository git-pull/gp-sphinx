"""Tests for the PEP 517 / 660 backend module.

The backend's job is exactly two things per hook:

1. Run the vite orchestration (``run_vite_build``).
2. Delegate to hatchling's matching hook.

These tests verify the order + delegation by patching both ``run_vite_build``
and the hatchling hooks; we never invoke a real wheel build here. End-to-end
sdist/wheel construction is exercised via ``uv build`` in CI.
"""

from __future__ import annotations

import typing as t

import hatchling.build as _hatchling
import pytest
from sphinx_vite_builder import build as backend


def _spy_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[str], dict[str, t.Any]]:
    """Patch ``run_vite_build`` and every hatchling hook with order-tracking spies.

    Returns
    -------
    order
        A shared list that records ``"vite"`` then ``"hatchling-<hook>"`` in the
        sequence each spy fired. Each ``build_*`` test asserts on its prefix.
    spies
        The hatchling-side spies, keyed by hook name. Tests can read their
        ``calls`` attribute to confirm forwarded args.
    """
    order: list[str] = []
    spies: dict[str, t.Any] = {}

    def _spy_run_vite_build(*_args: object, **_kwargs: object) -> None:
        order.append("vite")

    monkeypatch.setattr(backend, "run_vite_build", _spy_run_vite_build)

    def _make_hook_spy(name: str, return_value: str) -> t.Any:
        calls: list[tuple[tuple[t.Any, ...], dict[str, t.Any]]] = []

        def _spy(*args: t.Any, **kwargs: t.Any) -> str:
            order.append(f"hatchling-{name}")
            calls.append((args, kwargs))
            return return_value

        _spy.calls = calls  # type: ignore[attr-defined]
        return _spy

    for name, retval in (
        ("build_wheel", "fake-wheel.whl"),
        ("build_editable", "fake-editable.whl"),
        ("build_sdist", "fake-sdist.tar.gz"),
    ):
        spy = _make_hook_spy(name, retval)
        monkeypatch.setattr(_hatchling, name, spy)
        spies[name] = spy

    return order, spies


def test_build_wheel_runs_vite_then_delegates_to_hatchling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``build_wheel`` runs vite first, then hatchling's ``build_wheel``."""
    order, spies = _spy_pair(monkeypatch)
    result = backend.build_wheel("/tmp/wheels", {"foo": "bar"}, "/tmp/meta")
    assert order == ["vite", "hatchling-build_wheel"]
    assert result == "fake-wheel.whl"
    args, _kwargs = spies["build_wheel"].calls[0]
    assert args == ("/tmp/wheels", {"foo": "bar"}, "/tmp/meta")


def test_build_editable_runs_vite_then_delegates_to_hatchling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``build_editable`` runs vite first, then hatchling's ``build_editable``."""
    order, spies = _spy_pair(monkeypatch)
    result = backend.build_editable("/tmp/editable", None, None)
    assert order == ["vite", "hatchling-build_editable"]
    assert result == "fake-editable.whl"
    args, _kwargs = spies["build_editable"].calls[0]
    assert args == ("/tmp/editable", None, None)


def test_build_sdist_runs_vite_then_delegates_to_hatchling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``build_sdist`` runs vite first so the sdist contains pre-baked static."""
    order, spies = _spy_pair(monkeypatch)
    result = backend.build_sdist("/tmp/sdists", None)
    assert order == ["vite", "hatchling-build_sdist"]
    assert result == "fake-sdist.tar.gz"
    args, _kwargs = spies["build_sdist"].calls[0]
    assert args == ("/tmp/sdists", None)


def test_optional_hooks_alias_hatchling_directly() -> None:
    """The optional metadata/requires hooks have no vite concern."""
    assert (
        backend.get_requires_for_build_wheel is _hatchling.get_requires_for_build_wheel
    )
    assert (
        backend.get_requires_for_build_sdist is _hatchling.get_requires_for_build_sdist
    )
    assert (
        backend.get_requires_for_build_editable
        is _hatchling.get_requires_for_build_editable
    )
    assert (
        backend.prepare_metadata_for_build_wheel
        is _hatchling.prepare_metadata_for_build_wheel
    )
    assert (
        backend.prepare_metadata_for_build_editable
        is _hatchling.prepare_metadata_for_build_editable
    )


def test_backend_module_exposes_all_pep517_660_hooks() -> None:
    """The backend module's public surface covers every PEP 517 + 660 hook."""
    expected: set[str] = {
        "build_wheel",
        "build_editable",
        "build_sdist",
        "get_requires_for_build_wheel",
        "get_requires_for_build_sdist",
        "get_requires_for_build_editable",
        "prepare_metadata_for_build_wheel",
        "prepare_metadata_for_build_editable",
    }
    public = {n for n in dir(backend) if not n.startswith("_")}
    missing = expected - public
    assert not missing, f"backend missing hooks: {missing}"
