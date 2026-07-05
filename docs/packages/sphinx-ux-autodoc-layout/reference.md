(sphinx-ux-autodoc-layout-reference)=

# API Reference

## Config reference

Generated from {py:meth}`~sphinx.application.Sphinx.add_config_value`
registrations in
[`sphinx_ux_autodoc_layout/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-ux-autodoc-layout/src/sphinx_ux_autodoc_layout/__init__.py).

```{eval-rst}
.. autoconfigvalues:: sphinx_ux_autodoc_layout
```

## CSS classes

| Class | Element | Purpose |
|-------|---------|---------|
| `gp-sphinx-api-container` | `<dl>` | Managed autodoc shell |
| `gp-sphinx-api-header` | `<dt>` | Signature row shell |
| `gp-sphinx-api-content` | `<dd>` | Description/content shell |
| `gp-sphinx-api-layout` | `<div>` | Header split between left and right |
| `gp-sphinx-api-layout-left` | `<div>` | Signature text, custom disclosure, permalink |
| `gp-sphinx-api-layout-right` | `<div>` | Badge container and source link |
| `gp-sphinx-api-signature` | `<div>` | Compact signature row |
| `gp-sphinx-api-link` | `<a>` | Managed permalink in the left layout |
| `gp-sphinx-api-badge-container` | `<span>` | Wrapper for badge group output |
| `gp-sphinx-api-source-link` | `<span>` | Wrapper for the `[source]` link |
| `gp-sphinx-api-description` | `<div>` | Wraps paragraphs, notes, examples |
| `gp-sphinx-api-parameters` | `<div>` | Wraps field lists (Parameters, Returns) |
| `gp-sphinx-api-footer` | `<div>` | Wraps nested method/attribute entries |
| `gp-sphinx-api-region` | `<div>` | Compatibility alias on content sections |
| `gp-sphinx-api-region--narrative` | `<div>` | Compatibility alias on narrative sections |
| `gp-sphinx-api-region--fields` | `<div>` | Compatibility alias on parameter sections |
| `gp-sphinx-api-region--members` | `<div>` | Compatibility alias on footer/member sections |
| `gp-sphinx-api-fold` | `<details>` | Disclosure wrapper for large sections |
| `gp-sphinx-api-fold-summary` | `<summary>` | Click target showing field count |

## API reference

```{eval-rst}
.. autofunction:: sphinx_ux_autodoc_layout.build_api_card_entry

.. autofunction:: sphinx_ux_autodoc_layout.build_api_summary_section

.. autofunction:: sphinx_ux_autodoc_layout.build_api_table_section

.. autofunction:: sphinx_ux_autodoc_layout.build_api_facts_section
```

```{package-reference} sphinx-ux-autodoc-layout
```

## Extension entry point

```{eval-rst}
.. autofunction:: sphinx_ux_autodoc_layout.setup
```
