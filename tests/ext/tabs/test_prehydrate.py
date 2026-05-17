"""Tests for the sphinx-ux-tabs flash-of-wrong-selection prehydrate.

Covers three layers:

1. Pure-string generators (:func:`_build_style`, :func:`_script`) —
   no Sphinx app, no docutils tree.
2. The ``html-page-context`` hook short-circuit when no sync'd tabs
   were collected for the page.
3. An integration build with two sync'd tab-sets in
   ``:sync-group: shell`` — assert the ``<head>`` carries the prehydrate
   payload, and a page with no sync'd tabs does not.
"""

from __future__ import annotations

import textwrap
import typing as t

import pytest

from sphinx_ux_tabs._prehydrate import (
    ENV_ATTR,
    HTML_ATTR_PREFIX,
    LAYER_NAME,
    STORAGE_PREFIX,
    _build_style,
    _script,
    init_env_store,
    inject_tabs_prehydrate,
    record_pair,
)
from tests._sphinx_scenarios import (
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

# ---------------------------------------------------------------------------
# _build_style — unit tests
# ---------------------------------------------------------------------------


def test_build_style_wraps_rules_in_dedicated_layer() -> None:
    """The emitted block carries an ``@layer gp-sphinx-tabs-prehydrate`` wrapper."""
    style = _build_style([("shell", "bash")])
    assert style.startswith("<style>")
    assert style.endswith("</style>")
    assert f"@layer {LAYER_NAME} {{" in style


def test_build_style_emits_label_and_panel_rules_per_pair() -> None:
    """Each ``(group, id)`` pair lands as two rules (label and panel)."""
    style = _build_style([("shell", "bash")])
    # The <html> attribute selector keys both rules on the saved id.
    assert 'html[data-gp-sphinx-tabs-sync-shell="bash"]' in style
    # Label rule paints the active brand colour.
    assert (
        '.gp-sphinx-tabs__label[data-sync-id="bash"][data-sync-group="shell"]' in style
    )
    assert "color: var(--color-brand-primary)" in style
    assert "border-bottom-color: var(--color-brand-primary)" in style
    assert "background: var(--color-background-primary)" in style
    # Panel rule reveals the matching panel.
    assert (
        '.gp-sphinx-tabs__panel[data-sync-id="bash"][data-sync-group="shell"]' in style
    )
    assert "display: block" in style


def test_build_style_handles_multiple_pairs() -> None:
    """Multiple pairs produce two rules each, in stable order."""
    style = _build_style([("shell", "bash"), ("shell", "zsh")])
    for sync_id in ("bash", "zsh"):
        assert f'html[data-gp-sphinx-tabs-sync-shell="{sync_id}"]' in style
        assert (
            f'.gp-sphinx-tabs__label[data-sync-id="{sync_id}"][data-sync-group="shell"]'
            in style
        )
        assert (
            f'.gp-sphinx-tabs__panel[data-sync-id="{sync_id}"][data-sync-group="shell"]'
            in style
        )


def test_build_style_empty_input_returns_empty_string() -> None:
    """An empty iterable yields an empty string — caller appends unconditionally."""
    assert _build_style([]) == ""


def test_build_style_dedupes_repeated_pairs() -> None:
    """Repeated ``(group, id)`` pairs collapse to a single pair emission (label rule + panel rule)."""
    style = _build_style([("shell", "bash"), ("shell", "bash")])
    # One pair → two CSS rules (label + panel); each rule carries the html[...] anchor once.
    assert style.count('html[data-gp-sphinx-tabs-sync-shell="bash"]') == 2


# ---------------------------------------------------------------------------
# _script — unit tests
# ---------------------------------------------------------------------------


def test_script_marks_inline_script_as_rocket_loader_immune() -> None:
    """``data-cfasync="false"`` opts the inline script out of Rocket Loader."""
    script = _script({"shell"})
    assert 'data-cfasync="false"' in script


def test_script_reads_localstorage_for_the_workspace_key() -> None:
    """The inline script consults ``localStorage`` under the workspace prefix."""
    script = _script({"shell"})
    assert "localStorage.getItem" in script
    assert STORAGE_PREFIX in script


def test_script_writes_html_data_attribute_for_each_group() -> None:
    """The script sets ``<html data-gp-sphinx-tabs-sync-<group>="<id>">``."""
    script = _script({"shell"})
    assert HTML_ATTR_PREFIX in script
    assert "setAttribute" in script


def test_script_wraps_storage_access_in_try_catch() -> None:
    """Storage and URL access throw in sandboxed contexts — both are guarded."""
    script = _script({"shell"})
    # Outer try/catch around the whole IIFE.
    assert "try{" in script
    assert "catch(_)" in script


def test_script_emits_groups_in_sorted_order() -> None:
    """Deterministic order — the emitted list is sorted alphabetically."""
    script = _script({"zsh", "abc", "shell"})
    abc_idx = script.index('"abc"')
    shell_idx = script.index('"shell"')
    zsh_idx = script.index('"zsh"')
    assert abc_idx < shell_idx < zsh_idx


def test_script_empty_input_returns_empty_string() -> None:
    """No sync groups → no script payload."""
    assert _script(set()) == ""
    # Empty-string entries are filtered out, too.
    assert _script({""}) == ""


# ---------------------------------------------------------------------------
# inject_tabs_prehydrate — hook short-circuit
# ---------------------------------------------------------------------------


class _FakeEnv:
    """Minimal stand-in for :class:`sphinx.environment.BuildEnvironment`."""


class _FakeApp:
    """Minimal stand-in for :class:`sphinx.application.Sphinx`."""

    def __init__(self) -> None:
        self.env = _FakeEnv()


def test_inject_prehydrate_no_op_when_env_store_unset() -> None:
    """A page on an env that never recorded anything emits nothing."""
    app = _FakeApp()
    context: dict[str, t.Any] = {}
    inject_tabs_prehydrate(t.cast("t.Any", app), "index", "page.html", context, None)
    assert "metatags" not in context


def test_inject_prehydrate_no_op_when_page_has_no_pairs() -> None:
    """A page with an empty pair set emits nothing — gated payload."""
    app = _FakeApp()
    # Seed the store but leave the page's set empty.
    init_env_store(app.env)
    context: dict[str, t.Any] = {"metatags": "<!-- pre-existing -->"}
    inject_tabs_prehydrate(t.cast("t.Any", app), "index", "page.html", context, None)
    # No append happened.
    assert context["metatags"] == "<!-- pre-existing -->"


def test_inject_prehydrate_appends_style_and_script_when_pairs_present() -> None:
    """A page with recorded pairs gets both the ``<style>`` and ``<script>``."""
    app = _FakeApp()
    record_pair(app.env, "index", "shell", "bash")
    record_pair(app.env, "index", "shell", "zsh")
    context: dict[str, t.Any] = {}
    inject_tabs_prehydrate(t.cast("t.Any", app), "index", "page.html", context, None)
    metatags = context["metatags"]
    assert f"@layer {LAYER_NAME}" in metatags
    assert "<script" in metatags
    assert 'data-cfasync="false"' in metatags
    assert STORAGE_PREFIX in metatags


# ---------------------------------------------------------------------------
# Integration build — assert <head> carries the prehydrate
# ---------------------------------------------------------------------------


_PREHYDRATE_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    extensions = [
        "myst_parser",
        "sphinx_ux_tabs",
    ]
    myst_enable_extensions = ["colon_fence"]
    """,
)

_PREHYDRATE_INDEX_MD = textwrap.dedent(
    """\
    # Prehydrate sync demo

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

    ::::{tab-set}
    :sync-group: shell

    :::{tab-item} Bash
    :sync: bash
    second bash body
    :::

    :::{tab-item} Zsh
    :sync: zsh
    second zsh body
    :::

    ::::
    """,
)

_PREHYDRATE_PLAIN_MD = textwrap.dedent(
    """\
    # Plain tabs — no sync

    ::::{tab-set}

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
def prehydrate_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a synced + non-synced project for prehydrate <head> assertions."""
    cache_root = tmp_path_factory.mktemp("tabs-prehydrate")
    scenario = SphinxScenario(
        buildername="html",
        files=(
            ScenarioFile("conf.py", _PREHYDRATE_CONF_PY),
            ScenarioFile("index.md", _PREHYDRATE_INDEX_MD),
            ScenarioFile("plain.md", _PREHYDRATE_PLAIN_MD),
        ),
    )
    return build_shared_sphinx_result(cache_root, scenario)


@pytest.mark.integration
def test_synced_page_head_carries_prehydrate_style_block(
    prehydrate_html_result: SharedSphinxResult,
) -> None:
    """The synced page's ``<head>`` contains the prehydrate ``<style>``."""
    html = read_output(prehydrate_html_result, "index.html")
    head = html.split("</head>", 1)[0]
    assert f"@layer {LAYER_NAME}" in head
    assert 'html[data-gp-sphinx-tabs-sync-shell="bash"]' in head
    assert 'html[data-gp-sphinx-tabs-sync-shell="zsh"]' in head
    assert (
        '.gp-sphinx-tabs__label[data-sync-id="bash"][data-sync-group="shell"]' in head
    )
    assert '.gp-sphinx-tabs__panel[data-sync-id="zsh"][data-sync-group="shell"]' in head


@pytest.mark.integration
def test_synced_page_head_carries_inline_script(
    prehydrate_html_result: SharedSphinxResult,
) -> None:
    """The inline ``<script>`` is present and references the workspace key."""
    html = read_output(prehydrate_html_result, "index.html")
    head = html.split("</head>", 1)[0]
    assert 'data-cfasync="false"' in head
    assert f"{STORAGE_PREFIX}" in head
    assert '"shell"' in head  # the script enumerates the shell group


@pytest.mark.integration
def test_plain_page_head_has_no_prehydrate_payload(
    prehydrate_html_result: SharedSphinxResult,
) -> None:
    """A page without sync'd tabs gets zero prehydrate payload."""
    html = read_output(prehydrate_html_result, "plain.html")
    assert LAYER_NAME not in html
    assert STORAGE_PREFIX not in html


@pytest.mark.integration
def test_prehydrate_pairs_recorded_on_env(
    prehydrate_html_result: SharedSphinxResult,
) -> None:
    """The post-transform stashed sync pairs onto ``env.gp_sphinx_tabs_sync_pairs``."""
    env = prehydrate_html_result.app.env
    store: dict[str, set[tuple[str, str]]] = getattr(env, ENV_ATTR)
    assert "index" in store
    assert store["index"] == {("shell", "bash"), ("shell", "zsh")}
    # The plain page has no entry (empty set never recorded).
    assert "plain" not in store or not store["plain"]
