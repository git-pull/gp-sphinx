(sphinx-autodoc-fastmcp-how-to)=

# How to

Use this extension when a FastMCP server should document its tools,
resources, prompts, generated schemas, toolset metadata, and cross-reference
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

## Declare your toolsets

Tools are badged from their tags, and this extension ships **no** default
vocabulary — it renders documentation for projects whose tags it does not
choose, so a default would badge one project's tools with another's words.
Declare `fastmcp_toolsets`:

```python
fastmcp_toolsets = (
    {
        "tag": "teardown",
        "tooltip": "Deletes objects; not reversible.",
        "icon": "\N{BOMB}",
    },
    {"tag": "execute", "tooltip": "Starts or drives a process."},
    "manage",
    "inspect",
)
```

Order is precedence: a tool carrying several of these tags is badged with the
first one listed. An entry may be a bare tag name or a mapping with a `tooltip`
and an `icon`. The `{fastmcp-summary}` directive groups its tables in the same
order, titling each section from the tag.

A tool carrying none of the tags renders **without** a toolset badge. Falling
back to a tag nobody assigned is the one answer a badge must never give, and
with no declared vocabulary that is every tool — which is the signal that the
setting is missing.

Each toolset gets the CSS class `gp-sphinx-fastmcp__toolset-<tag>`. Style the
tags your project uses in your own CSS.

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
