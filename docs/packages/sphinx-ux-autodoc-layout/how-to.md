(sphinx-ux-autodoc-layout-how-to)=

# How to

## Pipeline position

Hooks `doctree-resolved` at priority **600**, after `sphinx-autodoc-api-style`
at 500. Consumes the `api_slot` nodes that producer packages inject into
`desc_signature` during earlier transforms, and composes them into the final
`gp-sphinx-api-layout-right` subcomponent (badges, source link, permalink).

The extension also overrides Sphinx's built-in
{py:class}`~sphinx.addnodes.desc_signature` HTML visitor with
{py:meth}`~sphinx.application.Sphinx.add_node`. This is a
deliberate platform decision: taking ownership of signature rendering allows
the `gp-sphinx-api-link` permalink to be placed inside the managed layout rather than
appended by Sphinx's default handler.

| Event | Hook | Priority |
|-------|------|----------|
| `doctree-resolved` | `on_doctree_resolved` | 600 (after api-style at 500) |
| `object-description-transform` | — | not used |

## Downstream `conf.py`

With `gp-sphinx`:

```python
conf = merge_sphinx_config(
    project="my-project",
    version="1.0.0",
    copyright="2026, Your Name",
    source_repository="https://github.com/your-org/my-project/",
    extra_extensions=["sphinx_ux_autodoc_layout"],
    api_layout_enabled=True,
    api_collapsed_threshold=10,
)
```

Or without {py:func}`~gp_sphinx.config.merge_sphinx_config`:

```python
extensions = ["sphinx.ext.autodoc", "sphinx_ux_autodoc_layout"]
api_layout_enabled = True
```

## Find configuration values

The {doc}`reference` page lists the configuration values registered by the
extension.

## Shared helper surface

- {py:func}`~sphinx_ux_autodoc_layout.build_api_card_entry` builds the shared
  inner `gp-sphinx-api-*` shell for section-card consumers such as FastMCP.
- {py:func}`~sphinx_ux_autodoc_layout.build_api_summary_section` wraps summary
  and index tables in the shared `gp-sphinx-api-summary` region.
