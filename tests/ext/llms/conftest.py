"""Fixtures for sphinx_gp_llms integration tests."""

from __future__ import annotations

import json
import pathlib
import typing as t

import pytest

from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
)

_BASE_CONF = """\
project = "llms-test"
extensions = ["myst_parser", "sphinx_gp_llms"]
master_doc = "index"
source_suffix = {".md": "markdown"}
exclude_patterns = []
html_theme = "basic"
site_url = "https://example.org/"
"""

_INDEX = """\
# LLMs Test Project

A test project for LLM documentation outputs.

```{toctree}
:caption: Guide
:maxdepth: 1

quickstart
advanced
```

```{toctree}
:caption: Reference
:maxdepth: 1

api
```
"""

_QUICKSTART = """\
# Quickstart

Get started with the project quickly.

## Installation

Install via pip.

## Usage

Run the main command.
"""

_ADVANCED = """\
# Advanced Usage

Deep-dive into advanced features.
"""

_API = """\
# API Reference

The public API surface.

## Functions

Details about functions.

## Classes

Details about classes.
"""


class LlmsBuildResult(t.NamedTuple):
    """Result from an LLM extension build."""

    result: SharedSphinxResult
    llms_txt_path: pathlib.Path
    llms_full_path: pathlib.Path
    docs_json_path: pathlib.Path


@pytest.fixture(scope="module")
def llms_build(
    tmp_path_factory: pytest.TempPathFactory,
) -> LlmsBuildResult:
    """Build a synthetic Sphinx project with sphinx_gp_llms enabled."""
    cache_root = tmp_path_factory.mktemp("llms-build")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("conf.py", _BASE_CONF),
            ScenarioFile("index.md", _INDEX),
            ScenarioFile("quickstart.md", _QUICKSTART),
            ScenarioFile("advanced.md", _ADVANCED),
            ScenarioFile("api.md", _API),
        ),
    )
    result = build_shared_sphinx_result(cache_root, scenario)
    return LlmsBuildResult(
        result=result,
        llms_txt_path=result.outdir / "llms.txt",
        llms_full_path=result.outdir / "llms-full.txt",
        docs_json_path=result.outdir / "docs.json",
    )


@pytest.fixture(scope="module")
def llms_txt_content(llms_build: LlmsBuildResult) -> str:
    """Read llms.txt content."""
    return llms_build.llms_txt_path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def llms_full_content(llms_build: LlmsBuildResult) -> str:
    """Read llms-full.txt content."""
    return llms_build.llms_full_path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def docs_json_data(llms_build: LlmsBuildResult) -> dict[str, t.Any]:
    """Parse docs.json content."""
    return json.loads(  # type: ignore[no-any-return]
        llms_build.docs_json_path.read_text(encoding="utf-8"),
    )
