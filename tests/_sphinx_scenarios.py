"""Typed helpers for caching synthetic Sphinx test scenarios.

The integration suite contains several tests that synthesize tiny Sphinx
projects, build them, and then inspect HTML or environment state.  This module
provides two conservative reuse modes:

``build_shared_sphinx_result``
    Build a scenario once in a stable cache directory and reuse the completed
    result for read-only assertions.

``build_isolated_sphinx_result``
    Copy a cached source tree into an isolated temporary directory and build
    there when a test needs stronger file-level isolation.

``derive_sphinx_scenario_cache_root``
    Derives a stable per-session cache root from any ``tmp_path`` by using its
    parent directory.

``copy_scenario_tree``
    Materialize a scenario's source files into a directory without running a
    Sphinx build.

Pass ``purge_modules`` to ``build_shared_sphinx_result`` or
``build_isolated_sphinx_result`` for any synthetic Python module written into
the scenario's ``sys.path`` to prevent stale ``sys.modules`` entries from
polluting subsequent builds in the same test session.
"""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import pathlib
import shutil
import sys
import typing as t

from docutils import nodes
from sphinx.application import Sphinx

SCENARIO_SRCDIR_TOKEN = "__SCENARIO_SRCDIR__"

__all__ = [
    "SCENARIO_SRCDIR_TOKEN",
    "ScenarioFile",
    "SharedSphinxResult",
    "SphinxScenario",
    "build_isolated_sphinx_result",
    "build_shared_sphinx_result",
    "copy_scenario_tree",
    "derive_sphinx_scenario_cache_root",
    "get_doctree",
    "read_output",
]

ScenarioInputValue: t.TypeAlias = (
    str
    | int
    | float
    | bool
    | None
    | list["ScenarioInputValue"]
    | tuple["ScenarioInputValue", ...]
    | set["ScenarioInputValue"]
    | frozenset["ScenarioInputValue"]
    | dict[str, "ScenarioInputValue"]
)
FrozenScenarioValue: t.TypeAlias = (
    str
    | int
    | float
    | bool
    | None
    | tuple["FrozenScenarioValue", ...]
    | dict[str, "FrozenScenarioValue"]
)


@dataclasses.dataclass(frozen=True, slots=True)
class ScenarioFile:
    """Represent a source file written into a synthetic Sphinx project.

    Parameters
    ----------
    relative_path :
        File path relative to the synthetic scenario ``src`` directory.
    contents :
        File contents to write.
    substitute_srcdir :
        Whether to replace :data:`SCENARIO_SRCDIR_TOKEN` with the concrete
        scenario ``src`` directory when materializing the file.
    """

    relative_path: str
    contents: str
    substitute_srcdir: bool = False


@dataclasses.dataclass(frozen=True, slots=True)
class SphinxScenarioKey:
    """Stable cache key for a synthetic Sphinx scenario."""

    buildername: str
    files: tuple[ScenarioFile, ...]
    confoverrides: dict[str, FrozenScenarioValue]

    def digest(self) -> str:
        """Return a deterministic digest for the scenario."""
        payload = {
            "buildername": self.buildername,
            "files": [
                {
                    "relative_path": file.relative_path,
                    "contents": file.contents,
                    "substitute_srcdir": file.substitute_srcdir,
                }
                for file in self.files
            ],
            "confoverrides": self.confoverrides,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclasses.dataclass(frozen=True, slots=True)
class SphinxScenario:
    """Describe a synthetic Sphinx project build.

    Parameters
    ----------
    buildername :
        Builder name passed to :class:`sphinx.application.Sphinx`.
    files :
        Files to write into the synthetic source tree.
    confoverrides :
        Optional Sphinx ``confoverrides`` passed to the app constructor.
    """

    buildername: str = "html"
    files: tuple[ScenarioFile, ...] = ()
    confoverrides: dict[str, ScenarioInputValue] | None = None

    def cache_key(self) -> SphinxScenarioKey:
        """Return the normalized cache key for this scenario."""
        return SphinxScenarioKey(
            buildername=self.buildername,
            files=tuple(sorted(self.files, key=lambda file: file.relative_path)),
            confoverrides=_freeze_override_mapping(self.confoverrides),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class SharedSphinxResult:
    """Read-only metadata for a completed Sphinx build."""

    app: Sphinx
    srcdir: pathlib.Path
    outdir: pathlib.Path
    status: str
    warnings: str


_SHARED_RESULTS: dict[pathlib.Path, SharedSphinxResult] = {}


def derive_sphinx_scenario_cache_root(tmp_path: pathlib.Path) -> pathlib.Path:
    """Return a stable per-session cache directory derived from ``tmp_path``."""
    cache_root = tmp_path.parent / "sphinx-scenario-cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root


def build_shared_sphinx_result(
    cache_root: pathlib.Path,
    scenario: SphinxScenario,
    *,
    purge_modules: tuple[str, ...] = (),
) -> SharedSphinxResult:
    """Build ``scenario`` once and reuse the completed result.

    Parameters
    ----------
    cache_root :
        Stable cache root for the current pytest session.
    scenario :
        Synthetic Sphinx scenario description.
    purge_modules :
        Module names to remove from :mod:`sys.modules` before the initial build.
    """
    key = scenario.cache_key()
    scenario_root = cache_root / key.digest()
    cached = _SHARED_RESULTS.get(scenario_root)
    if cached is not None:
        return cached

    srcdir = scenario_root / "src"
    outdir = scenario_root / "out"
    doctreedir = scenario_root / ".doctrees"
    if scenario_root.exists():
        shutil.rmtree(scenario_root)
    srcdir.mkdir(parents=True)
    outdir.mkdir()
    doctreedir.mkdir()

    _write_scenario_tree(srcdir, scenario)
    _purge_modules(purge_modules)

    status_buf = io.StringIO()
    warning_buf = io.StringIO()
    app = Sphinx(
        srcdir=str(srcdir),
        confdir=str(srcdir),
        outdir=str(outdir),
        doctreedir=str(doctreedir),
        buildername=scenario.buildername,
        confoverrides=_clone_confoverrides(scenario.confoverrides),
        status=status_buf,
        warning=warning_buf,
        freshenv=True,
    )
    app.build()

    result = SharedSphinxResult(
        app=app,
        srcdir=srcdir,
        outdir=outdir,
        status=status_buf.getvalue(),
        warnings=warning_buf.getvalue(),
    )
    _SHARED_RESULTS[scenario_root] = result
    return result


def copy_scenario_tree(
    cache_root: pathlib.Path,
    scenario: SphinxScenario,
    destination_root: pathlib.Path,
) -> pathlib.Path:
    """Copy a cached source tree for ``scenario`` into ``destination_root``."""
    source_tree = _ensure_cached_source_tree(cache_root, scenario)
    srcdir = destination_root / "src"
    shutil.copytree(source_tree, srcdir)
    return srcdir


def build_isolated_sphinx_result(
    cache_root: pathlib.Path,
    tmp_path: pathlib.Path,
    scenario: SphinxScenario,
    *,
    purge_modules: tuple[str, ...] = (),
) -> SharedSphinxResult:
    """Build ``scenario`` in an isolated temporary directory."""
    srcdir = copy_scenario_tree(cache_root, scenario, tmp_path)
    outdir = tmp_path / "out"
    doctreedir = tmp_path / ".doctrees"
    outdir.mkdir()
    doctreedir.mkdir()

    _purge_modules(purge_modules)
    status_buf = io.StringIO()
    warning_buf = io.StringIO()
    app = Sphinx(
        srcdir=str(srcdir),
        confdir=str(srcdir),
        outdir=str(outdir),
        doctreedir=str(doctreedir),
        buildername=scenario.buildername,
        confoverrides=_clone_confoverrides(scenario.confoverrides),
        status=status_buf,
        warning=warning_buf,
        freshenv=True,
    )
    app.build()
    return SharedSphinxResult(
        app=app,
        srcdir=srcdir,
        outdir=outdir,
        status=status_buf.getvalue(),
        warnings=warning_buf.getvalue(),
    )


def get_doctree(
    result: SharedSphinxResult,
    docname: str,
    *,
    post_transforms: bool = False,
) -> nodes.document:
    """Return a detached doctree for ``docname`` from ``result``.

    Parameters
    ----------
    result :
        Completed Sphinx scenario result.
    docname :
        Document name to fetch from the built environment.
    post_transforms :
        Whether to apply post-transforms to a detached doctree copy.

    Returns
    -------
    nodes.document
        Deep-copied doctree safe for test assertions and mutation.
    """
    doctree = result.app.env.get_doctree(docname).deepcopy()
    if post_transforms:
        result.app.env.apply_post_transforms(doctree, docname)
    return doctree


def read_output(
    result: SharedSphinxResult,
    filename: str,
    *,
    encoding: str = "utf-8",
) -> str:
    """Read a builder output file from ``result.outdir``.

    Parameters
    ----------
    result :
        Completed Sphinx scenario result.
    filename :
        Output filename relative to the builder output directory.
    encoding :
        Text encoding used when reading the file.

    Returns
    -------
    str
        File contents.
    """
    return (result.outdir / filename).read_text(encoding=encoding)


def _ensure_cached_source_tree(
    cache_root: pathlib.Path,
    scenario: SphinxScenario,
) -> pathlib.Path:
    """Materialize and return the canonical source tree for ``scenario``."""
    source_root = cache_root / f"{scenario.cache_key().digest()}-source"
    if source_root.exists():
        return source_root

    source_root.mkdir(parents=True)
    _write_scenario_tree(source_root, scenario)
    return source_root


def _write_scenario_tree(srcdir: pathlib.Path, scenario: SphinxScenario) -> None:
    """Write ``scenario`` files into ``srcdir``."""
    for file in scenario.files:
        target = srcdir / file.relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        contents = file.contents
        if file.substitute_srcdir:
            contents = contents.replace(SCENARIO_SRCDIR_TOKEN, str(srcdir))
        target.write_text(contents, encoding="utf-8")


def _purge_modules(module_names: tuple[str, ...]) -> None:
    """Remove module names and their children from :mod:`sys.modules`."""
    for module_name in module_names:
        for key in list(sys.modules):
            if key == module_name or key.startswith(f"{module_name}."):
                del sys.modules[key]


def _freeze_override_mapping(
    overrides: dict[str, ScenarioInputValue] | None,
) -> dict[str, FrozenScenarioValue]:
    """Return a deterministic, JSON-serializable override mapping."""
    if overrides is None:
        return {}
    return {
        key: _freeze_override_value(value) for key, value in sorted(overrides.items())
    }


def _freeze_override_value(value: ScenarioInputValue) -> FrozenScenarioValue:
    """Freeze an override value into a deterministic form."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            key: _freeze_override_value(item) for key, item in sorted(value.items())
        }
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_override_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        frozen_items = [_freeze_override_value(item) for item in value]
        return tuple(sorted(frozen_items, key=repr))
    msg = f"unsupported override value: {value!r}"
    raise TypeError(msg)


def _clone_confoverrides(
    overrides: dict[str, ScenarioInputValue] | None,
) -> dict[str, object] | None:
    """Clone ``confoverrides`` into a fresh mutable mapping for Sphinx."""
    if overrides is None:
        return None
    return {key: _clone_override_value(value) for key, value in overrides.items()}


def _clone_override_value(value: ScenarioInputValue) -> object:
    """Return a recursively cloned override value."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_clone_override_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_clone_override_value(item) for item in value)
    if isinstance(value, set):
        return {_clone_override_value(item) for item in value}
    if isinstance(value, frozenset):
        return frozenset(_clone_override_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _clone_override_value(item) for key, item in value.items()}
    msg = f"unsupported override value: {value!r}"
    raise TypeError(msg)
