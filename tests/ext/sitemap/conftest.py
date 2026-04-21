"""Fixtures for gp_sitemap integration tests.

Builds a tiny Sphinx project via the shared scenario cache, overriding
``sitemap_*`` config values per case, and reads the emitted
``sitemap.xml`` for assertions.
"""

from __future__ import annotations

import pathlib
import typing as t
from xml.etree import ElementTree

import pytest

from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    derive_sphinx_scenario_cache_root,
)

_BASE_CONF = """\
project = "gp-sitemap-test"
extensions = ["myst_parser", "gp_sitemap"]
master_doc = "index"
source_suffix = {".md": "markdown"}
exclude_patterns = []
html_theme = "basic"
"""

_INDEX = "# Index page\n\nBody content.\n"
_ABOUT = "# About page\n\nSome facts.\n"
_DRAFT = "# Draft\n\nShould be excluded when sitemap_excludes is set.\n"


class SitemapBuildResult(t.NamedTuple):
    """Return value of ``build_sitemap_site``."""

    result: SharedSphinxResult
    sitemap_path: pathlib.Path
    tree: ElementTree.ElementTree[t.Any] | None


def _confoverrides_to_conf_py(overrides: dict[str, t.Any]) -> str:
    lines: list[str] = []
    for key, value in overrides.items():
        lines.append(f"{key} = {value!r}")
    return "\n".join(lines) + "\n"


@pytest.fixture
def build_sitemap_site(
    tmp_path: pathlib.Path,
) -> t.Callable[..., SitemapBuildResult]:
    """Return a helper that builds a synthetic sitemap-enabled Sphinx site."""

    def _build(
        *,
        conf_overrides: dict[str, t.Any] | None = None,
        buildername: str = "html",
        extra_files: tuple[ScenarioFile, ...] = (),
    ) -> SitemapBuildResult:
        cache_root = derive_sphinx_scenario_cache_root(tmp_path)
        conf = _BASE_CONF + _confoverrides_to_conf_py(conf_overrides or {})
        scenario = SphinxScenario(
            buildername=buildername,
            files=(
                ScenarioFile("conf.py", conf),
                ScenarioFile("index.md", _INDEX),
                ScenarioFile("about.md", _ABOUT),
                ScenarioFile("draft.md", _DRAFT),
                *extra_files,
            ),
            confoverrides={"extensions": ("myst_parser", "gp_sitemap")},
        )
        # Ensure toctree references each page so Sphinx includes them.
        scenario = SphinxScenario(
            buildername=buildername,
            files=(
                ScenarioFile(
                    "conf.py",
                    conf,
                ),
                ScenarioFile(
                    "index.md",
                    "# Index page\n\nBody content.\n\n"
                    "```{toctree}\n:maxdepth: 1\n\nabout\ndraft\n```\n",
                ),
                ScenarioFile("about.md", _ABOUT),
                ScenarioFile("draft.md", _DRAFT),
                *extra_files,
            ),
        )
        result = build_shared_sphinx_result(cache_root, scenario)
        sitemap_path = result.outdir / "sitemap.xml"
        tree = ElementTree.parse(sitemap_path) if sitemap_path.exists() else None
        return SitemapBuildResult(result=result, sitemap_path=sitemap_path, tree=tree)

    return _build
