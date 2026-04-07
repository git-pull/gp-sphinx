(sphinx-autodoc-layout)=

# sphinx-autodoc-layout

{bdg-warning-line}`Alpha`

Wraps contiguous `desc_content` runs into semantic `gal_region` nodes
and folds large parameter sections with native `<details>/<summary>`.
Does not modify `desc_signature`.

## Configuration

| Setting | Default | Meaning |
|---------|---------|---------|
| `gal_enabled` | `False` | Enables the transform |
| `gal_fold_parameters` | `True` | Folds large field-list sections |
| `gal_collapsed_threshold` | `10` | Minimum field count before folding |

```{package-reference} sphinx-autodoc-layout
```
