(sphinx-autodoc-fastmcp)=

# sphinx-autodoc-fastmcp

{bdg-warning-line}`Alpha` {bdg-link-secondary-line}`GitHub <https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-fastmcp>` {bdg-link-secondary-line}`PyPI <https://pypi.org/project/sphinx-autodoc-fastmcp/>`

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
fastmcp_collector_mode = "introspect"
```

`sphinx_autodoc_fastmcp` auto-loads `sphinx_autodoc_badges`,
`sphinx_autodoc_layout`, and `sphinx_typehints_gp`.

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
.. fastmcp-toolsummary::
```
````

Add inline cross-references in prose:

````myst
Use {tool}`list_sessions` for a linked badge, or {toolref}`delete_session`
for a plain inline reference.
````

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
.. fastmcp-toolsummary::
```

## Package reference

```{package-reference} sphinx-autodoc-fastmcp
```
