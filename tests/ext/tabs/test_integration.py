"""Integration tests for sphinx_ux_tabs.

Builds a tiny project that exercises both authoring styles — two
consecutive ``.. tab::`` directives (RST, sphinx-inline-tabs style) and
a ``{tab-set}`` block with two ``{tab-item}`` children (MyST,
sphinx-design style) — and asserts on the rendered HTML.
"""

from __future__ import annotations

import textwrap

import pytest

from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    extensions = [
        "myst_parser",
        "sphinx_ux_tabs",
    ]
    myst_enable_extensions = ["colon_fence"]
    """,
)

_INDEX_RST = textwrap.dedent(
    """\
    Tabs RST demo
    =============

    .. tab:: First

       Body of the first tab.

    .. tab:: Second

       Body of the second tab.
    """,
)

_PAGE_MYST_MD = textwrap.dedent(
    """\
    # Tabs MyST demo

    ::::{tab-set}

    :::{tab-item} Python
    Python body.
    :::

    :::{tab-item} Rust
    :selected:
    Rust body.
    :::

    ::::
    """,
)

_PAGE_SYNC_MD = textwrap.dedent(
    """\
    # Tabs sync-group demo

    ::::{tab-set}
    :sync-group: shell

    :::{tab-item} Bash
    :sync: bash
    echo hi
    :::

    :::{tab-item} Zsh
    :sync: zsh
    print -P %~
    :::

    ::::
    """,
)

_PAGE_REF_MD = textwrap.dedent(
    """\
    # Tabs ref demo

    ::::{tab-set}

    :::{tab-item} Python
    :name: py-tab
    Python body.
    :::

    :::{tab-item} Rust
    Rust body.
    :::

    ::::

    See {ref}`the python tab <py-tab>` for details.
    """,
)

_PAGE_LARGE_MD = textwrap.dedent(
    """\
    # Tabs large demo

    ::::{tab-set}
    :class: gp-sphinx-tabs--large

    :::{tab-item} Python
    Python body.
    :::

    :::{tab-item} Rust
    Rust body.
    :::

    ::::
    """,
)


@pytest.fixture(scope="module")
def tabs_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a small MyST + RST project exercising every tab authoring style."""
    cache_root = tmp_path_factory.mktemp("tabs-html")
    scenario = SphinxScenario(
        buildername="html",
        files=(
            ScenarioFile("conf.py", _CONF_PY),
            ScenarioFile("index.rst", _INDEX_RST),
            ScenarioFile("page-myst.md", _PAGE_MYST_MD),
            ScenarioFile("page-sync.md", _PAGE_SYNC_MD),
            ScenarioFile("page-ref.md", _PAGE_REF_MD),
            ScenarioFile("page-large.md", _PAGE_LARGE_MD),
        ),
    )
    return build_shared_sphinx_result(cache_root, scenario)


@pytest.mark.integration
def test_consecutive_tab_directives_render_one_tab_set(
    tabs_html_result: SharedSphinxResult,
) -> None:
    """Two consecutive ``.. tab::`` directives produce one tab-set div."""
    html = read_output(tabs_html_result, "index.html")
    assert html.count('class="gp-sphinx-tabs"') == 1
    # Two radio inputs (one per tab) within the same name group.
    assert html.count('type="radio"') >= 2
    assert 'name="gp-sphinx-tab-set-' in html


@pytest.mark.integration
def test_tab_set_block_renders_input_label_panel_triple(
    tabs_html_result: SharedSphinxResult,
) -> None:
    """``{tab-set}`` + ``{tab-item}`` emits the radio-input HTML structure."""
    html = read_output(tabs_html_result, "page-myst.html")
    assert 'class="gp-sphinx-tabs"' in html
    assert 'type="radio"' in html
    # Two tab labels with their classes.
    assert html.count("gp-sphinx-tabs__label") >= 2
    # Panel container class is applied.
    assert "gp-sphinx-tabs__panel" in html


@pytest.mark.integration
def test_label_for_attribute_matches_input_id(
    tabs_html_result: SharedSphinxResult,
) -> None:
    """Every ``<label for="...">`` matches a sibling input's ``id``."""
    import re

    html = read_output(tabs_html_result, "page-myst.html")
    label_fors = re.findall(r'<label[^>]*for="([^"]+)"', html)
    input_ids = re.findall(r'<input[^>]*id="([^"]+)"', html)
    assert label_fors
    assert input_ids
    for for_attr in label_fors:
        assert for_attr in input_ids, (
            f"<label for={for_attr!r}> has no matching <input id>"
        )


@pytest.mark.integration
def test_selected_tab_item_emits_checked_attribute(
    tabs_html_result: SharedSphinxResult,
) -> None:
    """An explicit ``:selected:`` lands as ``checked`` on the right input."""
    html = read_output(tabs_html_result, "page-myst.html")
    # The Rust tab is :selected: — its input must carry ``checked``.
    # Locate the "Rust" label's `for` attribute, then find its input.
    import re

    match = re.search(
        r'<input[^>]*id="([^"]+)"[^>]*>\s*<label[^>]*for="\1"[^>]*>\s*Rust',
        html,
    )
    assert match is not None, "Could not locate Rust tab input/label pair"
    rust_input_id = match.group(1)
    # The matching <input ... id="…" …checked> must exist.
    input_tag_match = re.search(
        r'<input[^>]*id="' + re.escape(rust_input_id) + r'"[^>]*>',
        html,
    )
    assert input_tag_match is not None
    assert "checked" in input_tag_match.group(0)


@pytest.mark.integration
def test_tabs_emit_no_sphinx_design_classes(
    tabs_html_result: SharedSphinxResult,
) -> None:
    """The package never emits the sphinx-design ``sd-tab-*`` classes."""
    html = read_output(tabs_html_result, "page-myst.html")
    assert "sd-tab-set" not in html
    assert "sd-tab-item" not in html
    assert "sd-tab-label" not in html


@pytest.mark.integration
def test_non_synced_tabs_emit_no_sync_attributes(
    tabs_html_result: SharedSphinxResult,
) -> None:
    """Tabs without ``:sync:`` / ``:sync-group:`` emit no ``data-sync-*``.

    Guards the conditional emission in the HTML visitor — a regression
    that emits empty ``data-sync-id=""`` / ``data-sync-group=""`` would
    let CSS attribute selectors match the wrong panel and break the
    prehydrate restore on every non-synced page.
    """
    html = read_output(tabs_html_result, "page-myst.html")
    assert "data-sync-id" not in html
    assert "data-sync-group" not in html


@pytest.mark.integration
def test_sync_group_lands_on_label_data_attribute(
    tabs_html_result: SharedSphinxResult,
) -> None:
    """``:sync-group: shell`` on a ``tab-set`` propagates to every label."""
    html = read_output(tabs_html_result, "page-sync.html")
    # Both labels AND both panels in the sync set carry
    # ``data-sync-group="shell"`` — 2 labels + 2 panels = 4 occurrences.
    assert html.count('data-sync-group="shell"') >= 4
    # And each one names its own sync-id (``bash`` / ``zsh``).
    assert 'data-sync-id="bash"' in html
    assert 'data-sync-id="zsh"' in html


@pytest.mark.integration
def test_sync_attributes_land_on_panel_div(
    tabs_html_result: SharedSphinxResult,
) -> None:
    """The panel ``<div>`` carries ``data-sync-id`` / ``data-sync-group`` too.

    The prehydrate restore reads the panel attributes (not the label
    attributes) so CSS attribute selectors can reveal the right panel
    before the JS hydrates.
    """
    import re

    html = read_output(tabs_html_result, "page-sync.html")
    # Find every panel <div> that carries the panel class — the bash
    # and zsh panels must each carry both sync data attributes.  Attribute
    # ordering is implementation-defined by ``starttag``; assert presence,
    # not ordering.
    panel_divs = re.findall(
        r'<div[^>]*class="[^"]*gp-sphinx-tabs__panel[^"]*"[^>]*>',
        html,
    )
    assert len(panel_divs) == 2, f"expected 2 panel divs, got {len(panel_divs)}"
    for sync_id in ("bash", "zsh"):
        match = next(
            (d for d in panel_divs if f'data-sync-id="{sync_id}"' in d),
            None,
        )
        assert match is not None, f"no panel <div> for sync-id={sync_id!r}"
        assert 'data-sync-group="shell"' in match


@pytest.mark.integration
def test_large_modifier_class_survives_class_option_round_trip(
    tabs_html_result: SharedSphinxResult,
) -> None:
    """``:class: gp-sphinx-tabs--large`` lands on the rendered tab-set div.

    The modifier class must be present alongside the default
    ``gp-sphinx-tabs`` class so the size-variant CSS selectors
    (``.gp-sphinx-tabs.gp-sphinx-tabs--large .gp-sphinx-tabs__label``)
    actually match.
    """
    import re

    html = read_output(tabs_html_result, "page-large.html")
    # Locate the tab-set wrapper <div> and grab its class attribute.
    match = re.search(
        r'<div[^>]*class="([^"]*gp-sphinx-tabs[^"]*)"',
        html,
    )
    assert match is not None, "tab-set <div> with gp-sphinx-tabs class not found"
    class_attr = match.group(1)
    classes = class_attr.split()
    assert "gp-sphinx-tabs" in classes
    assert "gp-sphinx-tabs--large" in classes


@pytest.mark.integration
def test_name_option_produces_resolvable_ref_anchor(
    tabs_html_result: SharedSphinxResult,
) -> None:
    """``:name:`` on a tab-item gives ``{ref}`` a valid anchor to resolve."""
    import re

    html = read_output(tabs_html_result, "page-ref.html")
    # The label must carry the registered id (attribute order is unspecified
    # by ``starttag`` so match either ``for=...id=...`` or ``id=...for=...``).
    assert re.search(r'<label[^>]*\bid="py-tab"', html) is not None, (
        "label with id='py-tab' not found"
    )
    # The ``{ref}`...<py-tab>``` must resolve to an anchor pointing at the
    # label's id.
    ref_match = re.search(
        r'<a[^>]*href="#py-tab"[^>]*>',
        html,
    )
    assert ref_match is not None, "{ref}`...<py-tab>` did not resolve to an anchor"
