# sphinx-autodoc-fastmcp

Sphinx extension that documents **FastMCP** tools with card-style `desc` layouts (aligned with `sphinx-autodoc-api-style`), safety badges, parameter tables, and cross-reference roles.

## Features

- **`fastmcp-tool`**: Renders a tool entry as an `mcp` domain `desc` (definition list card) plus a section for ToC and `{ref}` labels.
- **`fastmcp-tool-input`**: Parameter table for a tool (place after prose in MyST).
- **`fastmcp-toolsummary`**: Summary tables grouped by safety tier.
- **Roles**: `:tool:`, `:toolref:`, `:toolicon` / `:tooliconl` / `:tooliconr` / `:tooliconil` / `:tooliconir:`, `:badge:`

## Configuration

In `conf.py` after `sphinx_autodoc_fastmcp` is listed in `extensions`:

```python
fastmcp_tool_modules = [
    "myproject.tools.server_tools",
    "myproject.tools.session_tools",
]
fastmcp_area_map = {
    "server_tools": "sessions",
    "session_tools": "sessions",
}
fastmcp_model_module = "myproject.models"
fastmcp_model_classes = {"SessionInfo", "WindowInfo"}
fastmcp_section_badge_map = {"Inspect": "readonly", "Act": "mutating", "Destroy": "destructive"}
fastmcp_section_badge_pages = {"tools/index", "index"}
fastmcp_collector_mode = "register"  # or "introspect"
```

See the package docstrings and `sphinx_autodoc_fastmcp.setup()` for defaults.

## Dependencies

- Python 3.10+
- Sphinx

## License

MIT
