(sphinx-ux-autodoc-layout-how-to)=

# How to

## Pipeline position

Hooks `doctree-resolved` at priority **600**, after `sphinx-autodoc-api-style`
at 500. Consumes the `api_slot` nodes that producer packages inject into
`desc_signature` during earlier transforms, and composes them into the final
`gp-sphinx-api-layout-right` subcomponent (badges, source link, permalink).

The extension also overrides Sphinx's built-in `desc_signature` HTML visitor
(`app.add_node(addnodes.desc_signature, override=True, ...)`). This is a
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

Or without `merge_sphinx_config`:

```python
extensions = ["sphinx.ext.autodoc", "sphinx_ux_autodoc_layout"]
api_layout_enabled = True
```

## Configuration

Generated from `app.add_config_value()` registrations in
[`sphinx_ux_autodoc_layout/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-ux-autodoc-layout/src/sphinx_ux_autodoc_layout/__init__.py).

```{eval-rst}
.. autoconfigvalues:: sphinx_ux_autodoc_layout
```

## Shared helper surface

- `build_api_card_entry()` builds the shared inner `api-*` shell for
  section-card consumers such as FastMCP.
- `build_api_summary_section()` wraps summary and index tables in the shared
  `gp-sphinx-api-summary` region.
