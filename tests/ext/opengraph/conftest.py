"""Fixtures for sphinx_gp_opengraph integration tests.

Builds a tiny Sphinx project via the shared scenario cache (see
``tests/_sphinx_scenarios.py``), overriding ``ogp_*`` config values per
case. Returns a helper that reads ``index.html`` and parses out its
``<meta>`` tags into a flat dict keyed by ``og:*`` / ``twitter:*`` /
``name="description"`` style keys.
"""

from __future__ import annotations

import pathlib
import re
import typing as t

import pytest

from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    derive_sphinx_scenario_cache_root,
    read_output,
)

_BASE_CONF = """\
project = "sphinx-gp-opengraph-test"
extensions = ["myst_parser", "sphinx_gp_opengraph"]
master_doc = "index"
source_suffix = {".md": "markdown"}
exclude_patterns = []
html_theme = "basic"
"""

_BASE_INDEX = """\
# Welcome to sphinx-gp-opengraph-test

This is the body paragraph that should become the og:description.

Another paragraph for good measure.
"""

_META_RE = re.compile(
    r'<meta\s+(property|name)="([^"]+)"\s+content="([^"]*)"\s*/?>',
    re.IGNORECASE,
)


class OgBuildResult(t.NamedTuple):
    """Return value of the ``build_og_site`` helper fixture."""

    result: SharedSphinxResult
    meta: dict[str, str]


def _confoverrides_to_conf_py(overrides: dict[str, t.Any]) -> str:
    """Serialize simple config overrides into Python assignments."""
    lines: list[str] = []
    for key, value in overrides.items():
        lines.append(f"{key} = {value!r}")
    return "\n".join(lines) + "\n"


def _parse_meta(html: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for _attr, key, value in _META_RE.findall(html):
        out[key] = value
    return out


@pytest.fixture
def build_og_site(
    tmp_path: pathlib.Path,
) -> t.Callable[..., OgBuildResult]:
    """Return a helper that builds a synthetic OG-enabled Sphinx site.

    The helper accepts optional ``conf_overrides`` (merged into the base
    ``conf.py``) and ``index_markdown`` (replaces the default body). It
    returns the completed build result plus a pre-parsed ``meta`` dict
    keyed on the meta tag's ``property`` / ``name`` attribute.
    """

    def _build(
        *,
        conf_overrides: dict[str, t.Any] | None = None,
        index_markdown: str | None = None,
    ) -> OgBuildResult:
        cache_root = derive_sphinx_scenario_cache_root(tmp_path)
        conf = _BASE_CONF + _confoverrides_to_conf_py(conf_overrides or {})
        index = index_markdown if index_markdown is not None else _BASE_INDEX
        scenario = SphinxScenario(
            files=(
                ScenarioFile("conf.py", conf),
                ScenarioFile("index.md", index),
            ),
        )
        result = build_shared_sphinx_result(cache_root, scenario)
        html = read_output(result, "index.html")
        return OgBuildResult(result=result, meta=_parse_meta(html))

    return _build
