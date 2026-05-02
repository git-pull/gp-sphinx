"""HTML byte-equivalence assertions: gp-furo-theme vs upstream Furo.

Two Sphinx scenarios build the same source tree against
``html_theme = "furo"`` and ``html_theme = "gp-furo"`` (in different
``cache_root`` directories so both wheels' static assets land on
disk simultaneously). The rendered ``*.html`` files are diffed for
byte-identity after normalising cache-busting query strings and
build-version comments.

CSS-equivalence assertions previously lived here too — they
compared ``_static/styles/furo.css`` byte-by-byte at the AST level
(custom-property declarations, selector sets per Furo surface,
no-preflight-leak guard). They were dropped in step 9.15 of the
2026-04-30 pivot:

- gp-furo no longer emits ``furo.css`` (the SCSS pipeline was
  removed in step 9.14; the new output is ``furo-tw.css``)
- visual fidelity now goes through ``tests/visual/test_visual_regression.py``
  (Playwright pixel-diff against captured baselines), not source
  AST comparison
- the new test cares about *rendered* surface, not source bytes —
  Tailwind preflight + Lightning CSS minification produce
  meaningfully different bytes than dart-sass output for the same
  visual result

The HTML half stays in tree because Furo's Jinja templates were
ported verbatim — modulo a 1-line attribution header per file —
so the rendered HTML structure remains directly comparable to
upstream Furo.
"""

from __future__ import annotations

import re
import textwrap

import pytest

# These tests build with `html_theme = "furo"` against upstream Furo for
# the equivalence comparison. After step 7's cutover, Furo is no longer
# a workspace dep — the tests stay in tree as a regression guard for
# anyone who installs `furo` and re-runs them, but skip cleanly when
# Furo isn't on `sys.path`.
pytest.importorskip("furo")

from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

# A tiny scenario chosen to exercise: a heading, a paragraph, an
# admonition (Furo-styled), an inline code span, a code block, a table.
# Keeps the build cheap (~0.5s) while touching a representative slice of
# the template surface.
_SCENARIO_INDEX = textwrap.dedent(
    """\
    Equivalence Demo
    ================

    Hello from a port-equivalence scenario.

    .. note::

       Port targets vanilla Furo's behavior 1:1.

    Inline code: ``foo``.

    .. code-block:: python

        def hello() -> None:
            print("hi")

    +---+---+
    | a | b |
    +===+===+
    | 1 | 2 |
    +---+---+
    """,
)

_FURO_CONF = textwrap.dedent(
    """\
    html_theme = "furo"
    master_doc = "index"
    project = "equivalence demo"
    """,
)

_GP_FURO_CONF = textwrap.dedent(
    """\
    html_theme = "gp-furo"
    master_doc = "index"
    project = "equivalence demo"
    """,
)


@pytest.fixture(scope="module")
def furo_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build the scenario against upstream Furo."""
    cache_root = tmp_path_factory.mktemp("equivalence-furo")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("conf.py", _FURO_CONF),
            ScenarioFile("index.rst", _SCENARIO_INDEX),
        ),
    )
    return build_shared_sphinx_result(cache_root, scenario)


@pytest.fixture(scope="module")
def gp_furo_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build the same scenario against the ported gp-furo theme."""
    cache_root = tmp_path_factory.mktemp("equivalence-gp-furo")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("conf.py", _GP_FURO_CONF),
            ScenarioFile("index.rst", _SCENARIO_INDEX),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("gp_furo_theme",),
    )


_DIGEST_RE = re.compile(r"\?digest=[0-9a-f]+")
_VERSION_RE = re.compile(r"\?v=[0-9a-f]+")
_GENERATOR_META_RE = re.compile(
    r'<meta name="generator" content="[^"]*"\s*/?>',
)
# Furo's `layout.html` template emits a build-time HTML comment
# `<!-- Generated with Sphinx X.Y.Z and Furo VERSION -->` that pulls
# `furo_version` from `_html_page_context`. Upstream is on
# `2025.12.19`, ours is workspace-locked to `0.0.1a12`.
_GENERATED_COMMENT_RE = re.compile(
    r"<!-- Generated with Sphinx [^>]+ and Furo [^>]+ -->",
)
# After step 9.14 dropped the SCSS pipeline, gp-furo emits
# `styles/furo-tw.css` while upstream Furo still emits `styles/furo.css`.
# The stylesheet path appears in every rendered page's <link rel> tag.
# Normalize so HTML byte-equivalence still holds at the structural level.
_FURO_STYLESHEET_RE = re.compile(r"/styles/furo(-tw)?\.css")


def _normalize_html(raw: str) -> str:
    """Normalize cache-busting hashes, version markers, and stylesheet path.

    Strip cache-busting digests, version hashes, version comments, and
    the post-9.14 stylesheet rename so the HTML byte-equivalence
    comparison still holds across the two themes.

    Sphinx applies two cache-busting schemes:
    - ``?digest=<sha1>`` on theme assets registered via
      ``_html_page_context``'s ``_add_asset_hashes`` (Furo's internal
      mechanism, only on Sphinx <7.1).
    - ``?v=<hex>`` on every other static asset (Sphinx core, modulo the
      file's content hash).

    Both are file-content-derived; different theme bundle bytes →
    different hashes. The generator meta names the active theme; the
    layout-emitted comment names both themes' versions. The stylesheet
    path differs because gp-furo's pure-Tailwind output is at
    ``styles/furo-tw.css`` while upstream is at ``styles/furo.css``.
    None of these affect functional equivalence.
    """
    s = _DIGEST_RE.sub("?digest=NORMALIZED", raw)
    s = _VERSION_RE.sub("?v=NORMALIZED", s)
    s = _GENERATOR_META_RE.sub(
        '<meta name="generator" content="NORMALIZED" />',
        s,
    )
    s = _GENERATED_COMMENT_RE.sub(
        "<!-- Generated with Sphinx NORMALIZED and Furo NORMALIZED -->",
        s,
    )
    s = _FURO_STYLESHEET_RE.sub("/styles/furo-NORMALIZED.css", s)
    return s


@pytest.mark.integration
def test_index_html_byte_equivalent(
    furo_html_result: SharedSphinxResult,
    gp_furo_html_result: SharedSphinxResult,
) -> None:
    """index.html is byte-identical after normalising digest + generator."""
    furo_html = _normalize_html(read_output(furo_html_result, "index.html"))
    gp_html = _normalize_html(read_output(gp_furo_html_result, "index.html"))
    assert furo_html == gp_html


@pytest.mark.integration
def test_search_html_byte_equivalent(
    furo_html_result: SharedSphinxResult,
    gp_furo_html_result: SharedSphinxResult,
) -> None:
    """search.html (no doctree) is byte-identical after normalisation."""
    furo_html = _normalize_html(read_output(furo_html_result, "search.html"))
    gp_html = _normalize_html(read_output(gp_furo_html_result, "search.html"))
    assert furo_html == gp_html


@pytest.mark.integration
def test_genindex_html_byte_equivalent(
    furo_html_result: SharedSphinxResult,
    gp_furo_html_result: SharedSphinxResult,
) -> None:
    """genindex.html (alternate index) is byte-identical after normalisation."""
    furo_html = _normalize_html(read_output(furo_html_result, "genindex.html"))
    gp_html = _normalize_html(read_output(gp_furo_html_result, "genindex.html"))
    assert furo_html == gp_html
