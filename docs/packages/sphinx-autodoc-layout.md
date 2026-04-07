(sphinx-autodoc-layout)=

# sphinx-autodoc-layout

{bdg-warning-line}`Alpha`

Wraps contiguous `desc_content` runs into semantic `gal_region` nodes
and folds large parameter sections with native `<details>/<summary>`.
Does not modify `desc_signature`.

## Live demo

```{py:module} gal_demo_api
```

### Small function (no fold)

```{eval-rst}
.. autofunction:: gal_demo_api.compact_function
```

### Class with members (regions + fold)

```{eval-rst}
.. autoclass:: gal_demo_api.LayoutDemo
   :members:
```

The class above should render with:

- **narrative** region (class docstring)
- **fields** region with fold (13 parameters > threshold of 10)
- **members** region (connect, execute, close methods)

## Configuration

| Setting | Default | Meaning |
|---------|---------|---------|
| `gal_enabled` | `False` | Enables the transform |
| `gal_fold_parameters` | `True` | Folds large field-list sections |
| `gal_collapsed_threshold` | `10` | Minimum field count before folding |

## CSS classes

| Class | Element | Purpose |
|-------|---------|---------|
| `gal-region` | `<div>` | Base class for all content regions |
| `gal-region--narrative` | `<div>` | Wraps paragraphs, notes, examples |
| `gal-region--fields` | `<div>` | Wraps field lists (Parameters, Returns) |
| `gal-region--members` | `<div>` | Wraps nested method/attribute entries |
| `gal-fold` | `<details>` | Disclosure wrapper for large sections |
| `gal-fold-summary` | `<summary>` | Click target showing field count |

```{package-reference} sphinx-autodoc-layout
```
