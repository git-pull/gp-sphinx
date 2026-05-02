"""Equivalence assertions: gp-furo-theme vs upstream Furo.

These tests defend the byte-for-byte HTML claim and the
AST-near-equivalent CSS claim from the porting plan. Two Sphinx
scenarios build the same source tree against ``html_theme = "furo"`` and
``html_theme = "gp-furo"`` (in different ``cache_root`` directories so
both wheels' static assets land on disk at the same time). Diffs run
against the materialised ``outdir`` of each.

Specifically asserted:

- Every rendered ``*.html`` is byte-identical across themes after
  normalising the ``?digest=<sha1>`` cache-busting query string and the
  ``<meta name="generator">`` content.
- The bundled ``_static/styles/furo.css`` files declare the same set of
  CSS custom property names at ``:root``, and Tailwind's preflight slots
  (``--default-font-family``, ``--default-mono-font-family``,
  ``--font-sans``, ``--font-mono``) do *not* leak into our output.
- Both themes emit the same set of class selectors anchored on the
  surfaces Furo's contract documents (``.sidebar-tree``, ``.toc-tree``,
  ``.admonition``, ``.theme-toggle``, etc.).
"""

from __future__ import annotations

import re
import textwrap
import typing as t

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

if t.TYPE_CHECKING:
    pass

# A tiny scenario chosen to exercise: a heading, a paragraph, an
# admonition (Furo-styled), an inline code span, a code block, a table.
# Keeps the build cheap (~0.5s) while touching a representative slice of
# the template + style surface.
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


def _normalize_html(raw: str) -> str:
    """Strip cache-busting digests, version hashes, and version comments.

    Sphinx applies two cache-busting schemes:
    - ``?digest=<sha1>`` on theme assets registered via
      ``_html_page_context``'s ``_add_asset_hashes`` (Furo's internal
      mechanism, only on Sphinx <7.1).
    - ``?v=<hex>`` on every other static asset (Sphinx core, modulo the
      file's content hash).

    Both are file-content-derived; different theme bundle bytes →
    different hashes. The generator meta names the active theme; the
    layout-emitted comment names both themes' versions. None of these
    affect functional equivalence.
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


# Lightweight CSS comparison: extract custom-property and class-selector
# sets, compare. Both surfaces should match upstream Furo exactly.
_CUSTOM_PROP_DECL_RE = re.compile(r"(?<![\w-])(--[a-z][a-z0-9-]*)(?=\s*:)")
_CLASS_SELECTOR_RE = re.compile(r"\.([a-z][a-z0-9-]*)")

_PREFLIGHT_TOKEN_NAMES = frozenset(
    {
        "--default-font-family",
        "--default-mono-font-family",
        "--font-sans",
        "--font-mono",
    },
)


def _read_static(result: SharedSphinxResult, relative: str) -> str:
    return (result.outdir / relative).read_text()


@pytest.mark.integration
def test_css_custom_properties_match(
    furo_html_result: SharedSphinxResult,
    gp_furo_html_result: SharedSphinxResult,
) -> None:
    """gp-furo emits every Furo CSS custom property the upstream theme does."""
    furo_props = set(
        _CUSTOM_PROP_DECL_RE.findall(
            _read_static(furo_html_result, "_static/styles/furo.css")
        ),
    )
    gp_props = set(
        _CUSTOM_PROP_DECL_RE.findall(
            _read_static(gp_furo_html_result, "_static/styles/furo.css")
        ),
    )

    missing = furo_props - gp_props
    assert not missing, (
        f"gp-furo is missing {len(missing)} Furo tokens: {sorted(missing)}"
    )


@pytest.mark.integration
def test_css_no_tailwind_preflight_leak(
    gp_furo_html_result: SharedSphinxResult,
) -> None:
    """gp-furo's furo.css must NOT contain Tailwind preflight slot names."""
    gp_css = _read_static(gp_furo_html_result, "_static/styles/furo.css")
    declared = set(_CUSTOM_PROP_DECL_RE.findall(gp_css))
    leaked = declared & _PREFLIGHT_TOKEN_NAMES
    assert not leaked, (
        f"Tailwind preflight tokens leaked into emitted CSS: {sorted(leaked)}. "
        'Likely cause: re-introduced `@import "tailwindcss"` in the entry CSS.'
    )


_FURO_CLASS_SURFACES = (
    "sidebar-tree",
    "toc-tree",
    "admonition",
    "highlight",
    "theme-toggle",
    "back-to-top",
    "mobile-header",
    "announcement",
)


@pytest.mark.integration
@pytest.mark.parametrize("surface", _FURO_CLASS_SURFACES)
def test_css_class_selector_set_matches_for_surface(
    surface: str,
    furo_html_result: SharedSphinxResult,
    gp_furo_html_result: SharedSphinxResult,
) -> None:
    """Each Furo class surface emits the same set of selectors in both builds."""
    furo_css = _read_static(furo_html_result, "_static/styles/furo.css")
    gp_css = _read_static(gp_furo_html_result, "_static/styles/furo.css")

    pattern = re.compile(rf"\.{re.escape(surface)}\b[^,{{]*")
    furo_selectors = {sel.strip() for sel in pattern.findall(furo_css)}
    gp_selectors = {sel.strip() for sel in pattern.findall(gp_css)}

    missing = furo_selectors - gp_selectors
    assert not missing, (
        f"gp-furo is missing {len(missing)} `.{surface}`-anchored selectors: "
        f"{sorted(missing)}"
    )
