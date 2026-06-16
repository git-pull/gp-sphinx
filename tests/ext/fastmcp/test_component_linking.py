"""Cross-reference linking coverage for FastMCP component directives & roles.

Locks issue #56's acceptance criteria. Tools/prompts already linked; this
suite proves the parity affordances for the non-tool families:

* resources, prompts, and resource templates register std-domain labels, so
  they land in ``objects.inv`` as ``std:label`` (intersphinx-reachable) and
  resolve via ``{ref}``
* ``:no-index:`` suppresses cross-document label registration so a component
  shown on more than one page keeps a single canonical home
"""

from __future__ import annotations

import textwrap
import typing as t

import pytest
from sphinx.util.inventory import InventoryFile

from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
)

# In-memory fastmcp-shaped fixture extension: stuffs one prompt, one resource,
# and one resource template onto ``app.env`` (priority >500 so it wins over
# ``collect_prompts_and_resources`` clearing the attributes). No real fastmcp
# dependency — the directives are what we exercise.
_FIXTURE_EXT = textwrap.dedent(
    '''\
    """In-memory fastmcp-shaped fixture extension for linking tests."""

    from __future__ import annotations

    import typing as t

    from sphinx.application import Sphinx

    from sphinx_autodoc_fastmcp._models import (
        PromptInfo,
        ResourceInfo,
        ResourceTemplateInfo,
    )


    def _populate(app: Sphinx) -> None:
        app.env.fastmcp_prompts = {
            "greet": PromptInfo(
                name="greet",
                title="Greet",
                description="Greet a user.",
                docstring="Greet a user.",
                tags=("ops",),
                arguments=[],
            )
        }
        app.env.fastmcp_resources = {
            "mem://hello": ResourceInfo(
                name="hello",
                uri="mem://hello",
                title="Hello",
                description="Static hello blob.",
                mime_type="text/markdown",
                docstring="Static hello blob.",
                tags=("readonly",),
            )
        }
        app.env.fastmcp_resource_names = {"hello": "mem://hello"}
        app.env.fastmcp_resource_templates = {
            "mem://user/{id}": ResourceTemplateInfo(
                name="user_record",
                uri_template="mem://user/{id}",
                title="User record",
                description="Per-user record.",
                mime_type="application/json",
                parameters=[],
                docstring="Per-user record.",
                tags=("readonly",),
            )
        }
        app.env.fastmcp_resource_template_names = {"user_record": "mem://user/{id}"}


    def setup(app: Sphinx) -> dict[str, t.Any]:
        app.connect("builder-inited", _populate, priority=600)
        return {"version": "0.1", "parallel_read_safe": True}
    '''
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations
    import sys
    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "myst_parser",
        "sphinx_autodoc_fastmcp",
        "fastmcp_link_fixture_ext",
    ]
    myst_enable_extensions = ["colon_fence"]
    fastmcp_tool_modules = []
    """
)

_DIRECTIVES_MD = textwrap.dedent(
    """\
    # FastMCP linking demo

    ```{fastmcp-prompt} greet
    ```

    ---

    ```{fastmcp-resource} hello
    ```

    ---

    ```{fastmcp-resource-template} user_record
    ```
    """
)


def _scenario(*files: ScenarioFile) -> SphinxScenario:
    """Assemble a scenario with the shared fixture extension + conf.py."""
    return SphinxScenario(
        files=(
            ScenarioFile("fastmcp_link_fixture_ext.py", _FIXTURE_EXT),
            ScenarioFile(
                "conf.py",
                _CONF_PY.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            *files,
        ),
    )


def _load_inventory(result: SharedSphinxResult) -> dict[str, dict[str, t.Any]]:
    """Parse the built ``objects.inv`` into ``{domain: {name: item}}``."""
    inv_path = result.outdir / "objects.inv"
    with inv_path.open("rb") as handle:
        return InventoryFile.load(handle, "", lambda base, target: target)


@pytest.fixture(scope="module")
def linking_html(tmp_path_factory: pytest.TempPathFactory) -> SharedSphinxResult:
    """Build the component-directives demo once per module."""
    cache_root = tmp_path_factory.mktemp("fastmcp-linking")
    scenario = _scenario(ScenarioFile("index.md", _DIRECTIVES_MD))
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("fastmcp_link_fixture_ext",),
    )


# --- objects.inv (issue #56 acceptance #2) ---------------------------------


class InventoryCase(t.NamedTuple):
    """One expected ``std:label`` inventory entry."""

    test_id: str
    label: str


_INVENTORY_CASES: list[InventoryCase] = [
    InventoryCase(test_id="prompt", label="fastmcp-prompt-greet"),
    InventoryCase(test_id="resource", label="fastmcp-resource-hello"),
    InventoryCase(
        test_id="resource-template",
        label="fastmcp-resource-template-user-record",
    ),
]


@pytest.mark.integration
@pytest.mark.parametrize(
    "case",
    _INVENTORY_CASES,
    ids=lambda c: c.test_id,
)
def test_component_label_lands_in_objects_inv(
    linking_html: SharedSphinxResult,
    case: InventoryCase,
) -> None:
    """Each component registers a ``std:label`` reachable via intersphinx."""
    inventory = _load_inventory(linking_html)
    assert case.label in inventory["std:label"], (
        f"{case.label} missing from objects.inv std:label entries"
    )


# --- :no-index: parity (issue #56 request) ---------------------------------

_NO_INDEX_INDEX_MD = textwrap.dedent(
    """\
    # No-index demo

    ```{toctree}
    canonical
    secondary
    ```
    """
)

_CANONICAL_MD = textwrap.dedent(
    """\
    # Canonical home

    ```{fastmcp-resource} hello
    ```
    """
)

_SECONDARY_MD = textwrap.dedent(
    """\
    # Secondary appearance

    ```{fastmcp-resource} hello
    :no-index:
    ```
    """
)


@pytest.fixture(scope="module")
def no_index_html(tmp_path_factory: pytest.TempPathFactory) -> SharedSphinxResult:
    """Build a resource shown on two pages, the second with ``:no-index:``."""
    cache_root = tmp_path_factory.mktemp("fastmcp-no-index")
    scenario = _scenario(
        ScenarioFile("index.md", _NO_INDEX_INDEX_MD),
        ScenarioFile("canonical.md", _CANONICAL_MD),
        ScenarioFile("secondary.md", _SECONDARY_MD),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("fastmcp_link_fixture_ext",),
    )


@pytest.mark.integration
def test_no_index_resource_keeps_single_canonical_home(
    no_index_html: SharedSphinxResult,
) -> None:
    """``:no-index:`` binds the canonical label to the page that omits it."""
    inventory = _load_inventory(no_index_html)
    item = inventory["std:label"]["fastmcp-resource-hello"]
    assert item.uri.startswith("canonical"), (
        f"canonical label should point at canonical page, got {item.uri!r}"
    )


@pytest.mark.integration
def test_no_index_resource_emits_no_duplicate_label_warning(
    no_index_html: SharedSphinxResult,
) -> None:
    """The opted-out page registers no competing label, so no duplicate warning."""
    assert "duplicate label" not in no_index_html.warnings.lower()
