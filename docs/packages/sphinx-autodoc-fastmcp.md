(sphinx-autodoc-fastmcp)=

# sphinx-autodoc-fastmcp

```{gp-sphinx-package-meta} sphinx-autodoc-fastmcp
```

:::{admonition} Alpha
:class: warning

Rendered output is stable. The Python API, CSS class names, and Sphinx
config value names may change without a major version bump. Pin your
dependency to a specific version range in production.
:::

Sphinx extension for documenting **FastMCP** tools: section cards built from
shared `api-*` layout regions, safety badges, parameter tables, and
cross-reference roles (`:tool:`, `:toolref:`, `:badge:`, etc.).

The shipped output intentionally keeps the outer `section` wrapper so table of
contents labels and tool references stay stable. Inside that wrapper, shared
layout, badge, and typehint helpers now own the visible card structure.

```console
$ pip install sphinx-autodoc-fastmcp
```

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

`sphinx_autodoc_fastmcp` automatically registers `sphinx_ux_badges`,
`sphinx_ux_autodoc_layout`, and `sphinx_autodoc_typehints_gp` via `app.setup_extension()`.
You do not need to add them separately to your `extensions` list.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `fastmcp_tool_modules` | `[]` | Python module paths that expose tool callables |
| `fastmcp_area_map` | `{}` | Maps module stem to area path for ToC labels |
| `fastmcp_collector_mode` | `"register"` | `"register"` or `"introspect"` — how tools are discovered |
| `fastmcp_server_module` | `""` | `"module.path:attr"` — live FastMCP instance for prompt/resource autodoc |
| `fastmcp_model_module` | `None` | Module containing Pydantic model classes |
| `fastmcp_model_classes` | `set()` | Set of model class names to cross-reference |
| `fastmcp_section_badge_map` | `{}` | Maps section names to safety badge labels |
| `fastmcp_section_badge_pages` | `set()` | Pages where section safety badges are injected |

### `fastmcp_server_module`

Pointing the collector at a live FastMCP instance enables autodoc of
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

## Working usage examples

Render one tool card:

````myst
```{eval-rst}
.. fastmcp-tool:: my_project.docs.fastmcp_tools.list_sessions
```
````

Render one tool's parameter table:

````myst
```{eval-rst}
.. fastmcp-tool-input:: my_project.docs.fastmcp_tools.list_sessions
```
````

Render a summary table grouped by safety tier:

````myst
```{eval-rst}
.. fastmcp-tool-summary::
```
````

Add inline cross-references in prose:

````myst
Use {tool}`list_sessions` for a linked badge, or {toolref}`delete_session`
for a plain inline reference.
````

### Prompts and resources

After setting `fastmcp_server_module`, four MyST directives become available
for documenting MCP prompts and resources:

````myst
```{fastmcp-prompt} my_prompt
```

```{fastmcp-prompt-input} my_prompt
```

```{fastmcp-resource} my_resource
```

```{fastmcp-resource-template} my_resource_template
```
````

Resources and resource templates accept either the friendly component name
(`my_resource`) or the literal URI (`mem://my_resource`). When two
distinct resources share a name, autodoc keeps the first registration and
emits a warning — disambiguate by URI.

### `:ref:` cross-reference IDs

Section IDs follow `fastmcp-{kind}-{name}` (canonical):

```text
{ref}`fastmcp-tool-list-sessions`
{ref}`fastmcp-prompt-greet`
{ref}`fastmcp-resource-status`
{ref}`fastmcp-resource-template-events-by-day`
```

Tool sections additionally register the bare slug as a back-compat alias
(e.g. `{ref}`list-sessions`` continues to resolve), preserving links
shipped before the kind-prefix introduction. Prompts, resources, and
resource templates use the canonical ID only — no bare alias is created
for them.

## Live demos

Use {tool}`list_sessions` for a linked badge, or {toolref}`delete_session`
for a plain inline reference.

### Tool cards

```{eval-rst}
.. fastmcp-tool:: fastmcp_demo_tools.list_sessions

.. fastmcp-tool:: fastmcp_demo_tools.create_session

.. fastmcp-tool:: fastmcp_demo_tools.delete_session
```

### Parameter table

```{eval-rst}
.. fastmcp-tool-input:: fastmcp_demo_tools.create_session
```

### Tool summary

```{eval-rst}
.. fastmcp-tool-summary::
```

## Config reference

Generated from `app.add_config_value()` registrations in
[`sphinx_autodoc_fastmcp/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-fastmcp/src/sphinx_autodoc_fastmcp/__init__.py).

```{eval-rst}
.. autoconfigvalues:: sphinx_autodoc_fastmcp
```

## Directive and role reference

Generated from `app.add_directive()` and `app.add_role()` registrations in
[`sphinx_autodoc_fastmcp/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-fastmcp/src/sphinx_autodoc_fastmcp/__init__.py)
via `sphinx-autodoc-docutils`.

```{eval-rst}
.. autodirectives:: sphinx_autodoc_fastmcp

.. autoroles:: sphinx_autodoc_fastmcp
```

## Package reference

```{package-reference} sphinx-autodoc-fastmcp
```
