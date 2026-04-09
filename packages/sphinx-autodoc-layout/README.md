# sphinx-autodoc-layout

Componentized layout for Sphinx autodoc output. It preserves Sphinx's
outer `dl / dt / dd` structure while rebuilding managed object-description
entries into stable `api-*` components. The current shared layout covers
Python API objects, pytest fixtures, Sphinx `confval` entries, docutils
`rst:*` entries, and internal FastMCP `mcp:tool` prototypes used to validate
future consolidation work.

The extension keeps header composition in a late `doctree-resolved` pass so
badges, source links, and permalinks can be positioned independently without
raw HTML mutation. Large signatures can fold into native multiline signature
markup, and expanded folded signatures show annotations by default via
`gal_signature_show_annotations`.
