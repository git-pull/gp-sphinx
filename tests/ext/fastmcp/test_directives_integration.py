"""Integration coverage for the four FastMCP MyST directives.

Builds one synthetic Sphinx project that registers a fake FastMCP-shaped
server (no real ``fastmcp`` dependency) via a tiny extension, renders all
four directives, and asserts the rendered HTML contains:

* canonical kind-prefixed section IDs (``fastmcp-{kind}-{name}``)
* the resource MIME pill
* the prompt argument table
* the resource-template parameter table inside the card section
  (sibling-adoption transform working)
* ``:ref:`` cross-references resolve to the canonical IDs and the build
  emits zero ``undefined label`` warnings
"""

from __future__ import annotations

import textwrap

import pytest
from docutils import nodes

from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    get_doctree,
    read_output,
)

# A minimal fake-extension that builds in-memory ``PromptInfo`` /
# ``ResourceInfo`` / ``ResourceTemplateInfo`` instances and stuffs them onto
# ``app.env.fastmcp_*`` directly. Bypasses ``_resolve_server_instance`` so
# we don't need a real fastmcp dep — the directives are what we want to
# exercise here.
_FAKE_EXT_SOURCE = textwrap.dedent(
    '''\
    """In-memory fastmcp-shaped fixture extension."""

    from __future__ import annotations

    import typing as t

    from sphinx.application import Sphinx

    from sphinx_autodoc_fastmcp._models import (
        PromptArgInfo,
        PromptInfo,
        ResourceInfo,
        ResourceTemplateInfo,
    )


    def _populate(app: Sphinx) -> None:
        prompts = {
            "greet": PromptInfo(
                name="greet",
                title="Greet",
                description="Greet a user.",
                docstring="Greet a user.",
                tags=("ops",),
                arguments=[
                    PromptArgInfo(
                        name="who",
                        description="Who to greet.",
                        required=True,
                        type_str="str",
                    ),
                ],
            )
        }
        resources = {
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
        templates = {
            "mem://user/{id}": ResourceTemplateInfo(
                name="user_record",
                uri_template="mem://user/{id}",
                title="User record",
                description="Per-user record.",
                mime_type="application/json",
                parameters=[
                    PromptArgInfo(
                        name="id",
                        description="User identifier.",
                        required=True,
                        type_str="str",
                    ),
                ],
                docstring="Per-user record.",
                tags=("readonly",),
            )
        }
        app.env.fastmcp_prompts = prompts
        app.env.fastmcp_resources = resources
        app.env.fastmcp_resource_names = {"hello": "mem://hello"}
        app.env.fastmcp_resource_templates = templates
        app.env.fastmcp_resource_template_names = {
            "user_record": "mem://user/{id}",
        }


    def setup(app: Sphinx) -> dict[str, t.Any]:
        # Run AFTER sphinx_autodoc_fastmcp's collect_prompts_and_resources
        # has cleared the env attributes — connect to builder-inited with
        # the priority lever (>500) so we win.
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
        "fastmcp_fixture_ext",
    ]
    myst_enable_extensions = ["colon_fence"]
    fastmcp_tool_modules = []
    """
)

_INDEX_MD = textwrap.dedent(
    """\
    # FastMCP demo

    See {ref}`fastmcp-prompt-greet`, {ref}`fastmcp-resource-hello`, and
    {ref}`fastmcp-resource-template-user-record`.

    ```{fastmcp-prompt} greet
    ```

    ```{fastmcp-prompt-input} greet
    ```

    ---

    ```{fastmcp-resource} hello
    ```

    ---

    ```{fastmcp-resource-template} user_record
    ```
    """
)


@pytest.fixture(scope="module")
def fastmcp_directives_html(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build the demo doc once per module."""
    cache_root = tmp_path_factory.mktemp("fastmcp-directives")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("fastmcp_fixture_ext.py", _FAKE_EXT_SOURCE),
            ScenarioFile(
                "conf.py",
                _CONF_PY.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.md", _INDEX_MD),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("fastmcp_fixture_ext",),
    )


@pytest.mark.integration
def test_card_section_ids_use_canonical_prefix(
    fastmcp_directives_html: SharedSphinxResult,
) -> None:
    """Each directive emits a section with the canonical ``fastmcp-{kind}-{name}`` id."""
    html = read_output(fastmcp_directives_html, "index.html")
    assert 'id="fastmcp-prompt-greet"' in html
    assert 'id="fastmcp-resource-hello"' in html
    assert 'id="fastmcp-resource-template-user-record"' in html


@pytest.mark.integration
def test_resource_mime_pill_renders(
    fastmcp_directives_html: SharedSphinxResult,
) -> None:
    """Resource cards expose their MIME type via the dedicated pill class."""
    html = read_output(fastmcp_directives_html, "index.html")
    assert "text/markdown" in html
    assert "gp-sphinx-api-facts" in html


@pytest.mark.integration
def test_prompt_argument_table_renders(
    fastmcp_directives_html: SharedSphinxResult,
) -> None:
    """The prompt argument table emits the parameter name + description."""
    html = read_output(fastmcp_directives_html, "index.html")
    assert "who" in html
    assert "Who to greet." in html


@pytest.mark.integration
def test_resource_template_param_table_inside_card(
    fastmcp_directives_html: SharedSphinxResult,
) -> None:
    """Sibling-adoption transform pulls the template's param table inside the card section."""
    doctree = get_doctree(fastmcp_directives_html, "index")
    sections = [
        s
        for s in doctree.findall(nodes.section)
        if "fastmcp-resource-template-user-record" in s.get("ids", [])
    ]
    assert sections, "resource-template card section missing"
    section = sections[0]
    tables = list(section.findall(nodes.table))
    assert tables, "expected at least one parameter table inside the card section"


@pytest.mark.integration
def test_ref_xrefs_resolve_with_no_undefined_labels(
    fastmcp_directives_html: SharedSphinxResult,
) -> None:
    """All three :ref: targets resolve to the canonical IDs and emit no warnings."""
    html = read_output(fastmcp_directives_html, "index.html")
    assert 'href="#fastmcp-prompt-greet"' in html
    assert 'href="#fastmcp-resource-hello"' in html
    assert 'href="#fastmcp-resource-template-user-record"' in html
    assert "undefined label" not in fastmcp_directives_html.warnings
