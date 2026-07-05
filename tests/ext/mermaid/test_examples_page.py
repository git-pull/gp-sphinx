"""The examples gallery embeds every committed diagram with no renderer."""

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
    read_output,
)

pytestmark = pytest.mark.integration

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_EXT_DIR = _REPO_ROOT / "docs" / "_ext"
_PKG_SRC = _REPO_ROOT / "packages" / "sphinx-gp-mermaid" / "src"
_RENDERED_DIR = _REPO_ROOT / "packages" / "sphinx-gp-mermaid" / "examples" / "rendered"
_SRC_DIR = _REPO_ROOT / "packages" / "sphinx-gp-mermaid" / "examples" / "src"

_EXAMPLE_STEMS: tuple[str, ...] = tuple(
    sorted(path.stem for path in _SRC_DIR.glob("*.mmd"))
)

_CONF_PY = f"""\
import sys

sys.path.insert(0, r"{_EXT_DIR}")
sys.path.insert(0, r"{_PKG_SRC}")
extensions = ["myst_parser", "sphinx_gp_mermaid", "mermaid_examples"]
html_theme = "basic"
myst_enable_extensions = ["colon_fence"]
"""

_INDEX_MD = """\
# Examples

```{mermaid-examples}
```
"""


@pytest.fixture(scope="module")
def examples_page_build(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build the mermaid-examples gallery once for HTML assertions."""
    cache_root = tmp_path_factory.mktemp("mermaid-examples-page")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("conf.py", _CONF_PY),
            ScenarioFile("index.md", _INDEX_MD),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("mermaid_examples",),
    )


@pytest.fixture(scope="module")
def examples_page_html(examples_page_build: SharedSphinxResult) -> str:
    """Return the built ``index.html`` contents."""
    return read_output(examples_page_build, "index.html")


def test_examples_page_does_not_invoke_renderer(
    examples_page_build: SharedSphinxResult,
    examples_page_html: str,
) -> None:
    """The gallery embeds committed SVGs — no mmdc warning, no fallback."""
    assert "mermaid render unavailable" not in examples_page_build.warnings
    assert "gp-sphinx-mermaid__fallback" not in examples_page_html


def test_examples_page_embeds_every_diagram(examples_page_html: str) -> None:
    """One dual-theme figure per committed source."""
    count = len(_EXAMPLE_STEMS)
    assert count >= 10
    assert examples_page_html.count('data-mermaid-responsive="fit"') == count
    assert examples_page_html.count("gp-sphinx-mermaid__variant--theme-light") == count
    assert examples_page_html.count("gp-sphinx-mermaid__variant--theme-dark") == count


class ExampleStemCase(t.NamedTuple):
    """One example stem whose committed light/dark SVGs must appear inline."""

    test_id: str
    stem: str


_EXAMPLE_STEM_CASES: list[ExampleStemCase] = [
    ExampleStemCase(test_id=stem, stem=stem) for stem in _EXAMPLE_STEMS
]


@pytest.mark.parametrize(
    "case",
    _EXAMPLE_STEM_CASES,
    ids=[c.test_id for c in _EXAMPLE_STEM_CASES],
)
def test_example_svgs_are_inlined_verbatim(
    case: ExampleStemCase,
    examples_page_html: str,
) -> None:
    """Each committed light and dark SVG id is inlined on the page verbatim."""
    for theme in ("light", "dark"):
        svg = (_RENDERED_DIR / f"{case.stem}.{theme}.svg").read_text(encoding="utf-8")
        match = re.search(rf'id="(mermaid-[0-9a-f]{{12}}-{theme})"', svg)
        assert match is not None, f"{case.stem}.{theme}: committed SVG lacks an id"
        assert match.group(1) in examples_page_html
