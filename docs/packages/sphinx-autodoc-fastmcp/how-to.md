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

# Optional: point at a live FastMCP server instance to autodoc its tools,
# prompts, resources, and resource templates. Format is "module.path:attr_name".
# Both an instance and a zero-arg factory callable are accepted.
fastmcp_server_module = "my_project.server:mcp"
```

## Classify your tools

A tool is classified on one or more **axes**. Each axis is independent, so a
tool takes at most one term per axis and renders one badge per axis. That is
the difference from a single vocabulary: risk and topic can disagree without
one having to win.

This extension ships no project vocabulary. It documents projects whose tags it
does not choose, so a default would badge one project's tools with another's
words.

### One axis from your tags

```python
fastmcp_axes = (
    {
        "name": "capability",
        "terms": (
            {
                "term": "teardown",
                "tooltip": "Deletes objects; not reversible.",
                "icon": "\N{BOMB}",
                "tone": "red",
            },
            {"term": "execute", "tooltip": "Starts or drives a process."},
            "manage",
            "inspect",
        ),
    },
)
```

`terms` order is precedence: a tool carrying several of them takes the first
listed. A term is a bare tag name or a mapping with `label`, `tooltip`, `icon`,
`tone`, `style`, `fill` and `classes`.

A tool matching no term renders **no** badge for that axis. Falling back to a
term nobody assigned is the one answer a badge must never give.

### Two axes at once

Tags often carry two ideas. Declare an axis for each and both badges render:

```python
fastmcp_axes = (
    {"name": "risk", "terms": ("mutating", "readonly")},
    {"name": "topic", "terms": ("lifecycle", "metrics", "thresholds")},
)
```

A read-only `lifecycle` tool now shows `readonly` *and* `lifecycle`, where a
single vocabulary would have to drop one.

### Axes from MCP's own metadata

`source` says where a term comes from. It defaults to `tags`:

| `source` | Reads |
| --- | --- |
| `tags` | the tool's `tags`, matched against the declared terms |
| `annotations` | `ToolAnnotations`, yielding `readonly`, `mutating` or `destructive` |
| `meta:<key>` | `meta[<key>]`, whatever the tool put there |

```python
fastmcp_axes = (
    {"name": "risk", "source": "annotations"},
    {"name": "since", "source": "meta:since"},
)
```

The `annotations` source follows the MCP spec: `destructiveHint` describes a
tool only once `readOnlyHint` is false, and an unset hint says nothing rather
than defaulting. A tool that sets no hints takes no term, so declaring this
axis costs nothing until your tools carry annotations.

### Colours, and adding your own

`tone` names a colour: `green`, `blue`, `amber`, `red` or `slate`, defaulting
to `slate`. Tones are three CSS layers, so you can enter at whichever you need.

Restyle a shipped tone by redefining its palette variables:

```css
:root {
  --gp-sphinx-fastmcp-tone-red-bg: #7f1d1d;
  --gp-sphinx-fastmcp-tone-red-border: #991b1b;
  --gp-sphinx-fastmcp-tone-red-text: #fef2f2;
}
```

Add a tone the extension does not ship by defining its class, then naming it:

```css
.gp-sphinx-fastmcp__toolset--tone-teal {
  --gp-sphinx-fastmcp-badge-bg: #0f766e;
  --gp-sphinx-fastmcp-badge-border: #14b8a6;
  --gp-sphinx-fastmcp-badge-text: #f0fdfa;
}
```

```python
{"term": "audit", "tone": "teal"}
```

Every badge also carries `gp-sphinx-fastmcp__axis-<axis>` and
`gp-sphinx-fastmcp__<axis>-<term>`, so you can style one axis or one term
directly without going through tones at all.

### Summary tables

`{fastmcp-tool-summary}` groups by one axis, defaulting to the first declared.
Name another to group by it instead:

````myst
```{eval-rst}
.. fastmcp-tool-summary:: topic
```
````

`sphinx_autodoc_fastmcp` automatically registers `sphinx_ux_badges`,
`sphinx_ux_autodoc_layout`, and `sphinx_autodoc_typehints_gp` via
{py:meth}`~sphinx.application.Sphinx.setup_extension`. You do not need to add
them separately to your `extensions` list.

## Live server collection

Pointing {confval}`fastmcp_server_module` at a live FastMCP instance enables autodoc of
**tools**, **prompts**, **resources**, and **resource templates** — see the four new
directives below. The collector accepts either:

* A live instance: `"my_project.server:mcp"` (where `mcp = FastMCP(...)`).
* A zero-argument factory: `"my_project.server:make_server"` returning a
  `FastMCP` instance.

Tools come from the server in preference to {confval}`fastmcp_tool_modules`, so a
tool the server serves is documented whether or not a module hook exposes it, and
each tool takes its area from its own function rather than from its position in
that list. Leave {confval}`fastmcp_server_module` unset to keep the
module-scanning modes.

If the resolved object is not a `FastMCP` (no `local_provider` attribute),
collection is skipped and a warning is logged. The collector also invokes
the server's `register_all` / `_register_all` hook (if exported) to
ensure components registered lazily appear in the docs; FastMCP's default
`on_duplicate="error"` policy is suppressed for this call.

FastMCP keys tools and prompts by name while permitting two registrations to
share one, so both are served. The docs index holds one entry per name: it keeps
the first and warns, naming the collision.

Server/module overlap follows the documented precedence without warning.

Every warning this extension raises goes through Sphinx's warning stream, so
`-W` fails the build on them and `-w` records them. Each carries a category
you can suppress individually through `suppress_warnings`:

| Category | Raised when |
| --- | --- |
| `fastmcp.duplicate` | Two components claim one name |
| `fastmcp.alias` | A tool's bare-slug alias is already claimed by another document's label |
| `fastmcp.axis` | An axis is unusable, or a tool matches no term on one |
| `fastmcp.config` | A `fastmcp_axes` entry is malformed |
| `fastmcp.xref` | A cross-reference cannot resolve, or resolves away from its canonical section |

Suppressing the parent `fastmcp` category silences all of them. A tool named
after one of Sphinx's built-in labels (`genindex`, `modindex`, `search`)
raises nothing: it can never claim the bare alias, cross-references resolve
the canonical id first, and there is no action an author could take.
