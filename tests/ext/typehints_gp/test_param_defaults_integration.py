"""Integration tests for synthetic-init parameter-default rendering."""

from __future__ import annotations

import re
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

    import dataclasses


    @dataclasses.dataclass
    class HookCounters:
        \"\"\"Synthetic-init dataclass exercising default_factory shapes.\"\"\"

        items: list[int] = dataclasses.field(default_factory=list)
        mapping: dict[str, int] = dataclasses.field(default_factory=dict)
        names: set[str] = dataclasses.field(default_factory=set)
        count: int = 5
    """
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx.ext.autodoc",
        "sphinx_autodoc_typehints_gp",
    ]

    autodoc_preserve_defaults = True
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    .. autoclass:: param_defaults_demo.HookCounters
       :members:
    """
)


@pytest.fixture(scope="module")
def factory_defaults_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a Sphinx project exercising dataclass default_factory rendering."""
    cache_root = tmp_path_factory.mktemp("param-defaults-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("param_defaults_demo.py", _MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _CONF_PY.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _INDEX_RST),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("param_defaults_demo",),
    )


@pytest.mark.integration
def test_dataclass_factory_defaults_render_as_source_text(
    factory_defaults_html_result: SharedSphinxResult,
) -> None:
    """Dataclass default_factory params render source text, not <factory>."""
    html = read_output(factory_defaults_html_result, "index.html")

    # The raw <factory> sentinel must not appear anywhere — the contract
    # of this fix.
    assert "&lt;factory&gt;" not in html
    assert "<factory>" not in html

    # The chosen source-text fragments do appear in the page (each one
    # may be split across xref / Text nodes by D6's post-transform, so
    # we look at the plain-text reduction).
    plain = re.sub(r"<[^>]+>", "", html)
    plain = plain.replace("&lt;", "<").replace("&gt;", ">").replace("&#160;", " ")
    plain = re.sub(r"\s+", " ", plain)
    assert "items: list[int] = []" in plain
    assert "mapping: dict[str, int] = {}" in plain
    assert "names: set[str] = set()" in plain
    assert "count: int = 5" in plain


@pytest.mark.integration
def test_dataclass_factory_defaults_use_default_value_span(
    factory_defaults_html_result: SharedSphinxResult,
) -> None:
    """The arglist parses cleanly so default_value spans exist after the fix."""
    html = read_output(factory_defaults_html_result, "index.html")

    # Stage A success criterion: the AST path produced default_value spans
    # rather than _pseudo_parse_arglist gluing name=value into one span.
    assert 'class="default_value"' in html or "default_value" in html
