(sphinx-autodoc-fastmcp)=

# sphinx-autodoc-fastmcp

{bdg-warning-line}`Alpha` {bdg-link-secondary-line}`GitHub <https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-fastmcp>` {bdg-link-secondary-line}`PyPI <https://pypi.org/project/sphinx-autodoc-fastmcp/>`

Sphinx extension for documenting **FastMCP** tools: card-style `desc` layouts
(aligned with {doc}`sphinx-autodoc-api-style`), safety badges, parameter tables,
and cross-reference roles (`:tool:`, `:toolref:`, `:badge:`, etc.).

```console
$ pip install sphinx-autodoc-fastmcp
```

## Features

- **Tool cards**: `mcp` / `tool` domain `desc` nodes with toolbar badges
- **Collectors**: `register(mcp)`-style modules or `introspect` mode for `@mcp.tool`
- **Configuration**: module list, area map, model classes for type cross-refs
- **MyST directives**: `fastmcp-tool`, `fastmcp-tool-input`, `fastmcp-toolsummary`

## Package reference

```{package-reference} sphinx-autodoc-fastmcp
```
