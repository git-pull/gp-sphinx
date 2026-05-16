"""Tests for :mod:`sphinx_vite_builder._internal.hooks`.

The hooks layer wires :func:`run_vite_build` to Sphinx's lifecycle.
Tests use a thin Sphinx-app stand-in (with ``.config``) and monkey-patch
``hooks.run_vite_build`` so each test runs without spawning a real
subprocess.
"""

from __future__ import annotations

import dataclasses
import pathlib
import typing as t

import pytest
from sphinx.errors import ExtensionError
from sphinx_vite_builder._internal import hooks
from sphinx_vite_builder._internal.errors import (
    PnpmMissingError,
    SphinxViteBuilderError,
    ViteFailedError,
)


@dataclasses.dataclass
class _FakeConfig:
    """The slice of ``app.config`` the hooks read."""

    sphinx_vite_builder_mode: str = "auto"
    sphinx_vite_builder_root: str | None = None


@dataclasses.dataclass
class _FakeApp:
    """Minimal stand-in for ``sphinx.application.Sphinx``."""

    config: _FakeConfig = dataclasses.field(default_factory=_FakeConfig)


def test_on_builder_inited_no_op_when_root_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No ``sphinx_vite_builder_root`` → ``run_vite_build`` never called."""
    app = _FakeApp(config=_FakeConfig(sphinx_vite_builder_root=None))

    def _fail(**_: t.Any) -> None:
        msg = "run_vite_build should not be called when vite_root is None"
        raise AssertionError(msg)

    monkeypatch.setattr(hooks, "run_vite_build", _fail)
    hooks.on_builder_inited(app)  # type: ignore[arg-type]


def test_on_builder_inited_calls_run_vite_build_with_project_root(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a root is configured, ``run_vite_build`` receives its parent.

    ``run_vite_build`` resolves ``web/`` relative to its
    ``project_root`` argument, and ``sphinx_vite_builder_root`` points
    at the ``web/`` dir itself — so the hook must pass ``web/``'s
    parent.
    """
    web_dir = tmp_path / "web"
    web_dir.mkdir()

    captured: dict[str, pathlib.Path | None] = {"project_root": None}

    def _capture(*, project_root: pathlib.Path) -> None:
        captured["project_root"] = project_root

    monkeypatch.setattr(hooks, "run_vite_build", _capture)

    app = _FakeApp(
        config=_FakeConfig(
            sphinx_vite_builder_mode="auto",
            sphinx_vite_builder_root=str(web_dir),
        ),
    )
    hooks.on_builder_inited(app)  # type: ignore[arg-type]

    assert captured["project_root"] == web_dir.parent


@pytest.mark.parametrize(
    "mode",
    ["auto", "dev", "prod"],
    ids=["mode-auto", "mode-dev", "mode-prod"],
)
def test_on_builder_inited_runs_one_shot_in_every_mode(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """The synchronous one-shot fires in every mode (auto / dev / prod).

    Both PROD and DEV-under-sphinx-autobuild funnel through
    :func:`run_vite_build` — there is no mode-specific spawn path.
    """
    web_dir = tmp_path / "web"
    web_dir.mkdir()

    calls: list[pathlib.Path] = []
    monkeypatch.setattr(
        hooks,
        "run_vite_build",
        lambda *, project_root: calls.append(project_root),
    )

    app = _FakeApp(
        config=_FakeConfig(
            sphinx_vite_builder_mode=mode,
            sphinx_vite_builder_root=str(web_dir),
        ),
    )
    hooks.on_builder_inited(app)  # type: ignore[arg-type]

    assert calls == [web_dir.parent]


@pytest.mark.parametrize(
    "exc_factory",
    [
        lambda: PnpmMissingError("pnpm not on PATH"),
        lambda: ViteFailedError("vite exit 1"),
        lambda: SphinxViteBuilderError("anything else"),
    ],
    ids=["PnpmMissingError", "ViteFailedError", "SphinxViteBuilderError"],
)
def test_on_builder_inited_wraps_known_failures_as_extension_error(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    exc_factory: t.Callable[[], SphinxViteBuilderError],
) -> None:
    """Wrap a ``SphinxViteBuilderError`` as a modname-tagged ExtensionError.

    Users see ``Extension error (sphinx_vite_builder)`` instead of
    the internal module path.
    """
    web_dir = tmp_path / "web"
    web_dir.mkdir()

    original_exc = exc_factory()

    def _raise(*, project_root: pathlib.Path) -> None:
        raise original_exc

    monkeypatch.setattr(hooks, "run_vite_build", _raise)

    app = _FakeApp(
        config=_FakeConfig(
            sphinx_vite_builder_mode="auto",
            sphinx_vite_builder_root=str(web_dir),
        ),
    )
    with pytest.raises(ExtensionError) as excinfo:
        hooks.on_builder_inited(app)  # type: ignore[arg-type]

    assert excinfo.value.modname == "sphinx_vite_builder"
    assert excinfo.value.__cause__ is original_exc


def test_on_build_finished_silent_on_success() -> None:
    """No exception → handler completes without raising."""
    app = _FakeApp()
    hooks.on_build_finished(app, exception=None)  # type: ignore[arg-type]


def test_on_build_finished_logs_exception_at_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exception → handler logs and does not raise.

    Uses a direct logger.debug capture rather than caplog because the
    Sphinx ``SphinxLoggerAdapter`` does not propagate to the root
    logger that caplog hooks into.
    """
    captured: list[tuple[str, tuple[t.Any, ...]]] = []
    monkeypatch.setattr(
        hooks.logger,
        "debug",
        lambda msg, *args: captured.append((msg, args)),
    )

    app = _FakeApp()
    exc = RuntimeError("boom")
    hooks.on_build_finished(app, exception=exc)  # type: ignore[arg-type]

    assert len(captured) == 1
    assert captured[0][1] == (exc,)
