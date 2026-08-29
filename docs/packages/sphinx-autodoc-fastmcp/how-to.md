(sphinx-autodoc-fastmcp-how-to)=

# How to

Use this extension when a FastMCP server should document its tools,
resources, prompts, generated schemas, safety metadata, and cross-reference
badges from live registration data.

## Downstream `conf.py`

```python
extensions = ["sphinx_autodoc_fastmcp"]

fastmcp_tool_modules = [
    "my_project.docs.fastmcp_tools",
]
fastmcp_area_map = {
    "fastmcp_tools": "api/tools",
}
fastmcp_collector_mode = "register"

# Optional: point at a live FastMCP server instance to autodoc its prompts,
# resources, and resource templates. Format is "module.path:attr_name".
# Both an instance and a zero-arg factory callable are accepted.
fastmcp_server_module = "my_project.server:mcp"
```

## Name your own safety tiers

Tools are badged from their tags. The default vocabulary is `destructive`,
`mutating`, `readonly`, in that precedence order — declare
`fastmcp_safety_tiers` when your project tags its tools differently:

```python
fastmcp_safety_tiers = (
    {"tag": "teardown", "tooltip": "Deletes tmux objects", "icon": "💣"},
    {"tag": "execute", "tooltip": "Runs a command in a pane"},
    "manage",
    "inspect",
)
```

Order is precedence: a tool carrying several of these tags is badged with the
first one listed. An entry may be a bare tag name or a mapping with a `tooltip`
and an `icon`.

A tool carrying none of the tags renders **without** a safety badge. The
alternative — falling back to the last tier — would badge a tool with a name
nobody gave it, and read-only is the worst possible guess for a tool the
vocabulary does not cover.

Each tier gets the CSS class `gp-sphinx-fastmcp__safety-<tag>`. The shipped
stylesheet colours the three default tiers; a project introducing new names
styles them in its own CSS.

`sphinx_autodoc_fastmcp` automatically registers `sphinx_ux_badges`,
`sphinx_ux_autodoc_layout`, and `sphinx_autodoc_typehints_gp` via
{py:meth}`~sphinx.application.Sphinx.setup_extension`. You do not need to add
them separately to your `extensions` list.

## Live server collection

Pointing {confval}`fastmcp_server_module` at a live FastMCP instance enables autodoc of
**prompts**, **resources**, and **resource templates** — see the four new
directives below. The collector accepts either:

* A live instance: `"my_project.server:mcp"` (where `mcp = FastMCP(...)`).
* A zero-argument factory: `"my_project.server:make_server"` returning a
  `FastMCP` instance.

If the resolved object is not a `FastMCP` (no `local_provider` attribute),
collection is skipped and a warning is logged. The collector also invokes
the server's `register_all` / `_register_all` hook (if exported) to
ensure components registered lazily appear in the docs; FastMCP's default
`on_duplicate="error"` policy is suppressed for this call.
