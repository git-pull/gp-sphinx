(sphinx-autodoc-fastmcp-examples)=

# Examples

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

### Resource cards

Read from the live server at {confval}`fastmcp_server_module`. `docs://changelog`
sets every MCP annotation, `docs://readme` sets none — annotation facts appear
only when the resource carries them.

```{eval-rst}
.. fastmcp-resource:: docs://changelog

.. fastmcp-resource:: docs://readme

.. fastmcp-resource-template:: docs://changelog/{version}
```

### Prompt card

```{eval-rst}
.. fastmcp-prompt:: summarize_release
```

## Demo module reference

The demo objects above, as plain Python API — the targets the
entries' `Python path` facts link to:

```{eval-rst}
.. automodule:: fastmcp_demo_tools
   :members:
```
