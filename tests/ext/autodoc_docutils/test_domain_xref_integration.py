"""Integration tests for docutils-domain cross-reference resolution.

Builds a two-page project: ``index.rst`` documents components (creating
domain targets), ``usage.rst`` cross-references them with
``:docutils:*:`` roles plus one deliberately dangling target so the
tests prove resolution actually runs.
"""

from __future__ import annotations

import textwrap

import pytest

from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

_MODULE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations

    from docutils.transforms import Transform


    class DemoXrefTransform(Transform):
        \"\"\"Reorder demo paragraphs for xref tests.\"\"\"

        default_priority = 421

        def apply(self):
            pass
    """
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx_autodoc_docutils",
    ]
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Component reference
    ===================

    .. toctree::

       usage

    .. autotransform:: demo_xref_components.DemoXrefTransform
    """
)

_USAGE_RST = textwrap.dedent(
    """\
    Usage
    =====

    See :docutils:transform:`DemoXrefTransform` for the short form and
    :docutils:transform:`demo_xref_components.DemoXrefTransform` for the
    qualified form.

    This one dangles: :docutils:transform:`MissingTransform`.
    """
)


@pytest.fixture(scope="module")
def docutils_xref_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build the two-page docutils-domain xref scenario."""
    cache_root = tmp_path_factory.mktemp("autodoc-docutils-xref")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("demo_xref_components.py", _MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _CONF_PY.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _INDEX_RST),
            ScenarioFile("usage.rst", _USAGE_RST),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("demo_xref_components",),
    )


def _xref_warnings(result: SharedSphinxResult) -> list[str]:
    """Return xref-resolution warning lines from a build result.

    Filters narrowly for actual resolution failures so unrelated build
    noise from earlier in-process Sphinx runs never false-matches.
    """
    return [
        line
        for line in result.warnings.splitlines()
        if "reference target not found" in line.lower()
        or "undefined label" in line.lower()
    ]


@pytest.mark.integration
def test_docutils_xrefs_resolve_without_warnings(
    docutils_xref_result: SharedSphinxResult,
) -> None:
    """Resolvable :docutils:transform: refs produce no warnings."""
    offending = [
        line
        for line in _xref_warnings(docutils_xref_result)
        if "MissingTransform" not in line
    ]
    assert offending == [], "Component cross-references produced warnings:\n" + (
        "\n".join(offending)
    )


@pytest.mark.integration
def test_dangling_docutils_xref_warns(
    docutils_xref_result: SharedSphinxResult,
) -> None:
    """A dangling :docutils:transform: ref warns, proving resolution runs."""
    dangling = [
        line
        for line in _xref_warnings(docutils_xref_result)
        if "MissingTransform" in line
    ]
    assert len(dangling) == 1


@pytest.mark.integration
def test_html_contains_resolved_component_links(
    docutils_xref_result: SharedSphinxResult,
) -> None:
    """Resolved refs become links pointing at the component anchor."""
    usage_html = read_output(docutils_xref_result, "usage.html")
    assert 'href="index.html#docutils-transform' in usage_html


@pytest.mark.integration
def test_domain_data_populated_after_build(
    docutils_xref_result: SharedSphinxResult,
) -> None:
    """The documented transform lands in the docutils domain data."""
    domain_data = docutils_xref_result.app.env.domaindata["docutils"]
    assert "demo_xref_components.DemoXrefTransform" in domain_data["transform"]
