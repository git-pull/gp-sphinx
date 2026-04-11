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

For shared consumers, the public helper surface now includes:

- `build_api_card_entry()` for section-card consumers that need the same inner
  `api-*` shell without becoming `desc` entries
- `build_api_summary_section()` for summary/index wrappers such as config and
  fixture tables

## Install

```console
$ pip install sphinx-autodoc-layout
```

## Usage

Standalone Sphinx project:

```python
extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_layout"]
gal_enabled = True
```

With `gp-sphinx`:

```python
conf = merge_sphinx_config(
    ...,
    extra_extensions=["sphinx_autodoc_layout"],
    gal_enabled=True,
)
```

## Documentation

See the [full documentation](https://gp-sphinx.git-pull.com/packages/sphinx-autodoc-layout/)
for configuration reference, CSS classes, and live demos.
