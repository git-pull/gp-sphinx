"""Tests for sphinx-gp-mermaid's non-HTML fallbacks and failure handling."""

from __future__ import annotations

import logging
import subprocess
import textwrap
import types
import typing as t

import pytest
from docutils import nodes

import sphinx_gp_mermaid as sgm
from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)


class FallbackTextCase(t.NamedTuple):
    """Node attributes and the expected alt-text stand-in."""

    test_id: str
    alt: str
    caption: str
    expected: str


_FALLBACK_TEXT_CASES: list[FallbackTextCase] = [
    FallbackTextCase(
        test_id="alt-wins",
        alt="session holds windows",
        caption="ignored",
        expected="[diagram: session holds windows]",
    ),
    FallbackTextCase(
        test_id="caption-fallback",
        alt="",
        caption="how it flows",
        expected="[diagram: how it flows]",
    ),
    FallbackTextCase(
        test_id="no-text",
        alt="",
        caption="",
        expected="[diagram]",
    ),
]


@pytest.mark.parametrize(
    "case",
    _FALLBACK_TEXT_CASES,
    ids=[c.test_id for c in _FALLBACK_TEXT_CASES],
)
def test_diagram_fallback_text(case: FallbackTextCase) -> None:
    """``_diagram_fallback_text`` prefers alt, falls back to caption."""
    node = sgm.mermaid_inline()
    node["alt"] = case.alt
    node["caption"] = case.caption
    assert sgm._diagram_fallback_text(node) == case.expected


def _make_text_translator() -> types.SimpleNamespace:
    """Return a text-translator stand-in collecting ``add_text`` calls."""
    ns = types.SimpleNamespace(texts=[])
    ns.add_text = ns.texts.append
    return ns


class VisitorCase(t.NamedTuple):
    """A non-HTML visitor with its translator stand-in and output reader."""

    test_id: str
    visit: t.Callable[[t.Any, sgm.mermaid_inline], None]
    make_translator: t.Callable[[], types.SimpleNamespace]
    get_output: t.Callable[[types.SimpleNamespace], str]
    expected: str


_VISITOR_CASES: list[VisitorCase] = [
    VisitorCase(
        test_id="text-builder",
        visit=sgm.text_visit_mermaid_inline,
        make_translator=_make_text_translator,
        get_output=lambda ns: "".join(ns.texts),
        expected="[diagram: how it flows]",
    ),
    VisitorCase(
        test_id="man-builder",
        visit=sgm.man_visit_mermaid_inline,
        make_translator=lambda: types.SimpleNamespace(body=[]),
        get_output=lambda ns: "".join(ns.body),
        expected="[diagram: how it flows]",
    ),
    VisitorCase(
        test_id="latex-builder-escapes",
        visit=sgm.latex_visit_mermaid_inline,
        make_translator=lambda: types.SimpleNamespace(
            body=[],
            encode=lambda s: f"<enc>{s}</enc>",
        ),
        get_output=lambda ns: "".join(ns.body),
        expected="<enc>[diagram: how it flows]</enc>",
    ),
    VisitorCase(
        test_id="texinfo-builder-escapes",
        visit=sgm.texinfo_visit_mermaid_inline,
        make_translator=lambda: types.SimpleNamespace(
            body=[],
            escape=lambda s: f"<esc>{s}</esc>",
        ),
        get_output=lambda ns: "".join(ns.body),
        expected="<esc>[diagram: how it flows]</esc>",
    ),
]


@pytest.mark.parametrize(
    "case",
    _VISITOR_CASES,
    ids=[c.test_id for c in _VISITOR_CASES],
)
def test_non_html_visitors_emit_alt_stand_in(case: VisitorCase) -> None:
    """Each non-HTML visitor emits the alt-text stand-in and skips the node."""
    node = sgm.mermaid_inline()
    node["alt"] = ""
    node["caption"] = "how it flows"
    translator = case.make_translator()

    with pytest.raises(nodes.SkipNode):
        case.visit(t.cast("t.Any", translator), node)

    assert case.get_output(translator) == case.expected


def test_warn_render_failure_memoizes_per_builder(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The render-failure warning fires once per builder, not per node."""
    node = sgm.mermaid_inline()
    exc = sgm.MermaidRendererMissing("no mmdc")
    first_builder = types.SimpleNamespace()
    second_builder = types.SimpleNamespace()

    with caplog.at_level(logging.WARNING):
        sgm._warn_render_failure(t.cast("t.Any", first_builder), node, exc)
        sgm._warn_render_failure(t.cast("t.Any", first_builder), node, exc)
        sgm._warn_render_failure(t.cast("t.Any", second_builder), node, exc)

    warnings = [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING
        and "mermaid render unavailable" in r.getMessage()
    ]
    assert len(warnings) == 2


def test_render_treats_permission_error_as_renderer_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: t.Any,
) -> None:
    """A resolved but non-executable mmdc degrades instead of crashing."""
    monkeypatch.setattr(sgm, "_resolve_mmdc", lambda app: [str(tmp_path / "mmdc")])

    def raise_permission_error(
        *args: object,
        **kwargs: object,
    ) -> t.NoReturn:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(subprocess, "run", raise_permission_error)
    config = types.SimpleNamespace(mermaid_cmd="", mermaid_puppeteer_config="")
    app = types.SimpleNamespace(confdir=str(tmp_path), config=config)

    with pytest.raises(sgm.MermaidRendererMissing):
        sgm._render(t.cast("t.Any", app), "flowchart LR a-->b", "{}")


_TEXT_CONF = textwrap.dedent(
    """\
    extensions = ["myst_parser", "sphinx_gp_mermaid"]
    """
)

_TEXT_INDEX = textwrap.dedent(
    """\
    # Demo

    ```{mermaid}
    :alt: session holds windows

    flowchart TD
        a --> b
    ```
    """
)


@pytest.fixture(scope="module")
def mermaid_text_build(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a minimal MyST project with the text builder."""
    cache_root = tmp_path_factory.mktemp("mermaid-text")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("conf.py", _TEXT_CONF),
            ScenarioFile("index.md", _TEXT_INDEX),
        ),
        buildername="text",
    )
    return build_shared_sphinx_result(cache_root, scenario)


@pytest.mark.integration
def test_text_builder_emits_alt_stand_in(
    mermaid_text_build: SharedSphinxResult,
) -> None:
    """A text build renders the diagram as its alt-text stand-in, not a crash."""
    output = read_output(mermaid_text_build, "index.txt")
    assert "[diagram: session holds windows]" in output
    assert "flowchart" not in output
