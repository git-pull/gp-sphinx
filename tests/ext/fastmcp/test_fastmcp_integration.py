"""Integration tests for sphinx_autodoc_fastmcp shared layout cards."""

from __future__ import annotations

import logging
import pathlib
import subprocess
import sys
import textwrap
import typing as t

import pytest

from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    copy_scenario_tree,
    read_output,
)

_MODULE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations

    import types


    def list_sessions(server: str, limit: int = 20) -> str:
        \"\"\"List sessions for one server.

        Parameters
        ----------
        server : str
            Server name.
        limit : int
            Maximum number of sessions to return.
        \"\"\"

        return "[]"


    list_sessions.__fastmcp__ = types.SimpleNamespace(
        name="list_sessions",
        title="List Sessions",
        tags={"readonly"},
        annotations=None,
    )
    """
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx_autodoc_fastmcp",
    ]

    fastmcp_tool_modules = ["demo_tools"]
    fastmcp_area_map = {"demo_tools": "api"}
    fastmcp_axes = (
        {
            "name": "risk",
            "terms": ("destructive", "mutating", "readonly"),
        },
    )
    fastmcp_collector_mode = "introspect"
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Tools
    =====

    Use :toolref:`list_sessions` for an inline link.

    .. fastmcp-tool:: demo_tools.list_sessions

    .. fastmcp-tool-input:: demo_tools.list_sessions
    """
)


@pytest.fixture(scope="module")
def duplicate_warning_builds(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[bool, tuple[int, str]]:
    """Build a duplicate registration with strict and suppressed diagnostics."""
    root = tmp_path_factory.mktemp("fastmcp-duplicate-warnings")
    results: dict[bool, tuple[int, str]] = {}
    for suppressed in (False, True):
        build_root = root / str(suppressed)
        conf = _CONF_PY + '\nfastmcp_tool_modules = ["demo_tools", "demo_tools"]\n'
        if suppressed:
            conf += 'suppress_warnings = ["fastmcp.duplicate"]\n'
        source = copy_scenario_tree(
            root / "cache",
            SphinxScenario(
                files=(
                    ScenarioFile("demo_tools.py", _MODULE_SOURCE),
                    ScenarioFile(
                        "conf.py",
                        conf.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                        substitute_srcdir=True,
                    ),
                    ScenarioFile("index.rst", _INDEX_RST),
                ),
            ),
            build_root,
        )
        warning_file = build_root / "warnings.txt"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "sphinx",
                "-W",
                "--keep-going",
                "-b",
                "dummy",
                "-w",
                str(warning_file),
                str(source),
                str(build_root / "output"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert warning_file.exists(), result.stderr
        results[suppressed] = (result.returncode, warning_file.read_text())
    return results


@pytest.mark.integration
@pytest.mark.parametrize("suppressed", [False, True])
def test_collector_warnings_obey_sphinx_warning_policy(
    duplicate_warning_builds: dict[bool, tuple[int, str]], suppressed: bool
) -> None:
    """A duplicate fails -W and reaches -w unless its category is suppressed."""
    returncode, warnings = duplicate_warning_builds[suppressed]
    assert returncode == (0 if suppressed else 1)
    if suppressed:
        assert warnings == ""
    else:
        assert "duplicate tool name 'list_sessions'" in warnings
        assert "[fastmcp.duplicate]" in warnings


@pytest.fixture(scope="module")
def fastmcp_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    cache_root = tmp_path_factory.mktemp("fastmcp-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("demo_tools.py", _MODULE_SOURCE),
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
        purge_modules=("demo_tools",),
    )


@pytest.mark.integration
def test_fastmcp_tool_cards_use_shared_layout(
    fastmcp_html_result: SharedSphinxResult,
) -> None:
    html = read_output(fastmcp_html_result, "index.html")

    assert 'class="gp-sphinx-fastmcp__tool-section gp-sphinx-api-card-shell"' in html
    assert (
        'class="gp-sphinx-api-entry gp-sphinx-api-card-entry gp-sphinx-api-profile--fastmcp-tool gp-sphinx-fastmcp__tool-entry"'
        in html
    )
    assert "gp-sphinx-api-layout--desktop" in html
    assert "gp-sphinx-api-layout--mobile" in html
    assert 'class="gp-sphinx-api-badge-container"' in html
    assert (
        'class="gp-sphinx-api-facts gp-sphinx-api-region gp-sphinx-api-region--facts gp-sphinx-fastmcp__body-section"'
        in html
    )
    assert 'class="headerlink gp-sphinx-api-link"' in html
    assert 'class="reference internal" href="#fastmcp-tool-list-sessions"' in html
    assert "Parameters" in html
    assert "readonly" in html
    assert "tool" in html


_COLLISION_MODULE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations

    import types


    def delete_buffer(name: str) -> str:
        \"\"\"Delete one buffer.

        Parameters
        ----------
        name : str
            Buffer name.
        \"\"\"

        return ""


    delete_buffer.__fastmcp__ = types.SimpleNamespace(
        name="delete_buffer",
        title="Delete buffer",
        tags={"destructive"},
        annotations=None,
    )
    """
)

_COLLISION_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx_autodoc_fastmcp",
    ]

    fastmcp_tool_modules = ["buffer_tools"]
    fastmcp_area_map = {"buffer_tools": "api"}
    fastmcp_axes = (
        {
            "name": "risk",
            "terms": ("destructive", "mutating", "readonly"),
        },
    )
    fastmcp_collector_mode = "introspect"
    """
)

# The page heading "Delete buffer" slugs to ``delete-buffer`` — the same
# bare alias the tool card claims for the ``delete_buffer`` tool.
_COLLISION_INDEX_RST = textwrap.dedent(
    """\
    Delete buffer
    =============

    Use :toolref:`delete_buffer` for an inline link, or
    :ref:`delete-buffer` for a bare label reference.

    .. fastmcp-tool:: buffer_tools.delete_buffer

    .. fastmcp-tool-summary::
    """
)


@pytest.fixture(scope="module")
def fastmcp_heading_collision_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a page whose heading slug matches a tool's bare alias."""
    cache_root = tmp_path_factory.mktemp("fastmcp-heading-collision")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("buffer_tools.py", _COLLISION_MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _COLLISION_CONF_PY.replace(
                    "__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN
                ),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _COLLISION_INDEX_RST),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("buffer_tools",),
    )


class CollisionRenderFixture(t.NamedTuple):
    """HTML fragment that must render when a heading shares the tool's slug."""

    test_id: str
    needle: str


_COLLISION_RENDER_FIXTURES: list[CollisionRenderFixture] = [
    CollisionRenderFixture(
        test_id="canonical-card-id",
        needle='id="fastmcp-tool-delete-buffer"',
    ),
    CollisionRenderFixture(
        test_id="tool-section-classes",
        needle='class="gp-sphinx-fastmcp__tool-section gp-sphinx-api-card-shell"',
    ),
    CollisionRenderFixture(
        test_id="badge-container",
        needle='class="gp-sphinx-api-badge-container"',
    ),
]


@pytest.mark.integration
@pytest.mark.parametrize(
    list(CollisionRenderFixture._fields),
    _COLLISION_RENDER_FIXTURES,
    ids=[f.test_id for f in _COLLISION_RENDER_FIXTURES],
)
def test_heading_collision_card_renders(
    fastmcp_heading_collision_result: SharedSphinxResult,
    test_id: str,
    needle: str,
) -> None:
    """Card markup survives a heading/alias slug collision."""
    html = read_output(fastmcp_heading_collision_result, "index.html")
    assert needle in html


@pytest.mark.integration
def test_heading_collision_emits_no_duplicate_id_diagnostic(
    fastmcp_heading_collision_result: SharedSphinxResult,
) -> None:
    """A same-slug heading + tool card produces no duplicate IDs (#48)."""
    assert "Duplicate ID" not in fastmcp_heading_collision_result.warnings


class CollisionAnchorFixture(t.NamedTuple):
    """Expected occurrence count for an anchor fragment under a slug collision."""

    test_id: str
    needle: str
    expected_count: int


_COLLISION_ANCHOR_FIXTURES: list[CollisionAnchorFixture] = [
    CollisionAnchorFixture(
        test_id="bare-id-owned-by-heading-only",
        needle='id="delete-buffer"',
        expected_count=1,
    ),
    # The toolref link wraps the tool name in <code>; the bare {ref}
    # link wraps the label title in <span class="std std-ref"> — the
    # trailing tag disambiguates the two resolution paths.
    CollisionAnchorFixture(
        test_id="toolref-targets-canonical-anchor",
        needle='class="reference internal" href="#fastmcp-tool-delete-buffer"><code',
        expected_count=1,
    ),
    CollisionAnchorFixture(
        test_id="bare-ref-targets-canonical-anchor",
        needle='class="reference internal" href="#fastmcp-tool-delete-buffer"><span',
        expected_count=1,
    ),
    CollisionAnchorFixture(
        test_id="summary-targets-canonical-anchor",
        needle='href="api/#fastmcp-tool-delete-buffer"',
        expected_count=1,
    ),
]


@pytest.mark.integration
@pytest.mark.parametrize(
    list(CollisionAnchorFixture._fields),
    _COLLISION_ANCHOR_FIXTURES,
    ids=[f.test_id for f in _COLLISION_ANCHOR_FIXTURES],
)
def test_heading_collision_anchor_counts(
    fastmcp_heading_collision_result: SharedSphinxResult,
    test_id: str,
    needle: str,
    expected_count: int,
) -> None:
    """The heading owns the bare anchor; tool links target the canonical id (#48)."""
    html = read_output(fastmcp_heading_collision_result, "index.html")
    assert html.count(needle) == expected_count


_UNMATCHED_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx_autodoc_fastmcp",
    ]

    fastmcp_tool_modules = ["demo_tools"]
    fastmcp_area_map = {"demo_tools": "api"}
    fastmcp_axes = ({"name": "risk", "terms": ("destructive", "mutating")},)
    fastmcp_collector_mode = "introspect"
    """
)

_UNMATCHED_INDEX_RST = textwrap.dedent(
    """\
    Tools
    =====

    Use :tool:`list_sessions` for a linked badge.

    .. fastmcp-tool:: demo_tools.list_sessions

    .. fastmcp-tool-summary::
    """
)


def _unmatched_scenario() -> SphinxScenario:
    """Scenario whose one tool is tagged outside the declared vocabulary."""
    return SphinxScenario(
        files=(
            ScenarioFile("demo_tools.py", _MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _UNMATCHED_CONF_PY.replace(
                    "__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN
                ),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _UNMATCHED_INDEX_RST),
        ),
    )


@pytest.mark.integration
def test_tool_role_omits_the_badge_for_a_tag_outside_the_vocabulary(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """An empty-label badge is worse than none: a blank pill claiming nothing."""
    cache_root = tmp_path_factory.mktemp("fastmcp-unmatched-toolset")
    result = build_shared_sphinx_result(
        cache_root,
        _unmatched_scenario(),
        purge_modules=("demo_tools",),
    )

    assert "gp-sphinx-fastmcp__toolset" not in read_output(result, "index.html")


@pytest.mark.integration
def test_the_summary_warns_when_it_drops_an_unmatched_tool(
    tmp_path_factory: pytest.TempPathFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A tool the summary cannot place must not vanish without a trace."""
    cache_root = tmp_path_factory.mktemp("fastmcp-unmatched-toolset-warn")
    with caplog.at_level(logging.WARNING, logger="sphinx_autodoc_fastmcp"):
        build_shared_sphinx_result(
            cache_root,
            _unmatched_scenario(),
            purge_modules=("demo_tools",),
        )

    messages = "\n".join(record.message for record in caplog.records)
    assert "omitted from fastmcp-tool-summary" in messages
    assert "list_sessions" in messages


@pytest.mark.integration
def test_summary_sections_anchor_on_the_axis_term(
    fastmcp_heading_collision_result: SharedSphinxResult,
) -> None:
    """A tag keeps one anchor whatever its rendered heading reads."""
    html = read_output(fastmcp_heading_collision_result, "index.html")

    assert 'id="fastmcp-risk-destructive"' in html


@pytest.mark.integration
def test_the_axes_survive_a_second_build_of_one_app(
    tmp_path: pathlib.Path,
) -> None:
    """Nothing may clear the vocabulary per build.

    Sphinx emits builder-inited once per app but build-finished after
    every build(), so installing on the former and clearing on the latter
    leaves every rebuild badging tools with no tooltip, icon or tone.
    """
    from sphinx.application import Sphinx

    from sphinx_autodoc_fastmcp._badges import build_axis_badge, use_axes

    src = tmp_path / "src"
    src.mkdir()
    (src / "conf.py").write_text(
        'extensions = ["sphinx_autodoc_fastmcp"]\n'
        'fastmcp_axes = ({"name": "risk", "terms": ({"term": "execute",'
        ' "tooltip": "Runs it", "tone": "red"},)},)\n',
    )
    (src / "index.rst").write_text("Tools\n=====\n")

    app = Sphinx(
        str(src),
        str(src),
        str(tmp_path / "out"),
        str(tmp_path / "out" / ".doctrees"),
        "html",
        status=None,
        warning=None,
    )
    app.build()
    app.build()

    try:
        badge = build_axis_badge("risk", "execute")
        assert badge["badge_tooltip"] == "Runs it"
        assert "gp-sphinx-fastmcp__toolset--tone-red" in badge["classes"]
    finally:
        use_axes(None)


_TWO_AXIS_MODULE = textwrap.dedent(
    """\
    from __future__ import annotations

    import types


    def start_run(script: str) -> str:
        \"\"\"Start a load test.\"\"\"

        return ""


    start_run.__fastmcp__ = types.SimpleNamespace(
        name="start_run",
        title="Start Run",
        tags={"mutating", "lifecycle"},
        annotations={"readOnlyHint": False, "destructiveHint": False},
        meta={"since": "1.2"},
    )
    """
)

_TWO_AXIS_CONF = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = ["sphinx_autodoc_fastmcp"]
    fastmcp_tool_modules = ["demo_tools"]
    fastmcp_area_map = {"demo_tools": "api"}
    fastmcp_collector_mode = "introspect"
    fastmcp_axes = (
        {"name": "risk", "source": "annotations"},
        {"name": "topic", "terms": ("lifecycle", "metrics")},
        {"name": "since", "source": "meta:since"},
    )
    """
)


@pytest.mark.integration
def test_a_tool_renders_one_badge_per_declared_axis(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Three sources classify one tool at once, and each gets its own badge.

    A single vocabulary has to pick one of these and drop the rest.
    """
    cache_root = tmp_path_factory.mktemp("fastmcp-two-axis")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("demo_tools.py", _TWO_AXIS_MODULE),
            ScenarioFile(
                "conf.py",
                _TWO_AXIS_CONF.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile(
                "index.rst",
                "Tools\n=====\n\n.. fastmcp-tool:: demo_tools.start_run\n",
            ),
        ),
    )
    html = read_output(
        build_shared_sphinx_result(cache_root, scenario, purge_modules=("demo_tools",)),
        "index.html",
    )

    # readOnlyHint False + destructiveHint False is "mutating" per the MCP spec.
    assert "gp-sphinx-fastmcp__risk-mutating" in html
    assert "gp-sphinx-fastmcp__topic-lifecycle" in html
    assert "gp-sphinx-fastmcp__since-1.2" in html


_RESERVED_MODULE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations

    import types


    def search(terms: str, limit: int = 20) -> str:
        \"\"\"Search prompt records.

        Parameters
        ----------
        terms : str
            Terms to match.
        limit : int
            Maximum number of results.
        \"\"\"

        return "[]"


    search.__fastmcp__ = types.SimpleNamespace(
        name="search",
        title="Search",
        tags={"readonly"},
        annotations=None,
    )
    """
)

_RESERVED_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx_autodoc_fastmcp",
    ]

    fastmcp_tool_modules = ["reserved_tools"]
    fastmcp_area_map = {"reserved_tools": "api"}
    fastmcp_collector_mode = "introspect"
    """
)

# ``search`` is a Sphinx built-in std label (the JS "Search Page"), seeded
# into StandardDomain before any document is read, so a tool's bare-slug
# alias can never claim it (#48 only covers same-document heading
# collisions). The tool role must resolve via the canonical
# ``fastmcp-tool-search`` section id, not silently link to the site search.
_RESERVED_INDEX_RST = textwrap.dedent(
    """\
    Reserved slug tools
    ===================

    Use :toolref:`search` for an inline link.

    .. fastmcp-tool:: reserved_tools.search
    """
)


@pytest.fixture(scope="module")
def fastmcp_reserved_slug_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a page with a tool whose slug collides with a reserved label."""
    cache_root = tmp_path_factory.mktemp("fastmcp-reserved-slug")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("reserved_tools.py", _RESERVED_MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _RESERVED_CONF_PY.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _RESERVED_INDEX_RST),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("reserved_tools",),
    )


class ReservedSlugFixture(t.NamedTuple):
    """Expected occurrence count for an href under a reserved-slug collision."""

    test_id: str
    needle: str
    expected_count: int


_RESERVED_SLUG_FIXTURES: list[ReservedSlugFixture] = [
    # The tool role targets its own canonical card anchor, not Sphinx's
    # reserved ``search`` built-in (the site-search page).
    ReservedSlugFixture(
        test_id="toolref-targets-canonical-anchor",
        needle='class="reference internal" href="#fastmcp-tool-search"><code',
        expected_count=1,
    ),
    # The bare slug must not resolve to the built-in "Search Page", which is
    # ``search.html`` in the html builder.
    ReservedSlugFixture(
        test_id="toolref-skips-builtin-search-page",
        needle='href="search.html"><code',
        expected_count=0,
    ),
    # The card's canonical anchor is present regardless (physical section id).
    ReservedSlugFixture(
        test_id="canonical-card-id-present",
        needle='id="fastmcp-tool-search"',
        expected_count=1,
    ),
]


@pytest.mark.integration
@pytest.mark.parametrize(
    list(ReservedSlugFixture._fields),
    _RESERVED_SLUG_FIXTURES,
    ids=[f.test_id for f in _RESERVED_SLUG_FIXTURES],
)
def test_reserved_slug_tool_ref_targets_canonical(
    fastmcp_reserved_slug_result: SharedSphinxResult,
    test_id: str,
    needle: str,
    expected_count: int,
) -> None:
    """A tool whose slug collides with a reserved label links to its card."""
    html = read_output(fastmcp_reserved_slug_result, "index.html")
    assert html.count(needle) == expected_count
