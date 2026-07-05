(sphinx-autodoc-fastmcp-tutorial)=

# Tutorial

## Document your first tool

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

Prompts and resources have the same affordance (without a safety badge, which
only tools carry). `{resource}` resolves a fixed resource or a resource
template by name; `{prompt}` resolves a prompt:

````myst
See the {resource}`status` resource, the {resource}`events_by_day` template,
and the {prompt}`greet` prompt. The `{resourceref}` / `{promptref}` spellings
are aliases mirroring `{toolref}`.
````

### Prompts and resources

After setting {confval}`fastmcp_server_module`,
{rst:dir}`fastmcp-prompt`, {rst:dir}`fastmcp-prompt-input`,
{rst:dir}`fastmcp-resource`, and {rst:dir}`fastmcp-resource-template`
become available for documenting MCP prompts and resources:

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

Each of these directives accepts the standard `:no-index:` flag. When a
prompt, resource, or resource template is shown on more than one page, add
`:no-index:` to every appearance except the canonical one so the card still
renders everywhere but registers its cross-reference target exactly once:

````myst
```{fastmcp-resource} my_resource
:no-index:
```
````

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
