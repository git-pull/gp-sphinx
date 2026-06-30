"""Integration tests for sphinx_autodoc_fastmcp shared layout cards."""

from __future__ import annotations

import textwrap
import typing as t

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
