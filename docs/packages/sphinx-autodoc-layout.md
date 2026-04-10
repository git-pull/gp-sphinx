(sphinx-autodoc-layout)=

# sphinx-autodoc-layout

{bdg-warning-line}`Alpha` {bdg-link-secondary-line}`GitHub <https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-layout>` {bdg-link-secondary-line}`PyPI <https://pypi.org/project/sphinx-autodoc-layout/>`

Wraps contiguous `desc_content` runs into semantic `gal_region` nodes
and rebuilds Python autodoc entries into stable `api-*` components.
Large field-list parameter sections still use native `<details>/<summary>`,
while inline signature expansion uses a custom disclosure that reveals
Sphinx's native multiline parameter-list rendering.

It is now the shared presenter for the whole autodoc family. `desc`-backed
entries use it directly, and section-card consumers reuse the same inner shell
through the public `build_api_card_entry()` helper.

```console
$ pip install sphinx-autodoc-layout
```

## Downstream `conf.py`

```python
conf = merge_sphinx_config(
    project="my-project",
    version="1.0.0",
    copyright="2026, Your Name",
    source_repository="https://github.com/your-org/my-project/",
    extra_extensions=["sphinx_autodoc_layout"],
    gal_enabled=True,
    gal_collapsed_threshold=10,
)
```

## Working usage examples

Render one compact function:

````myst
```{eval-rst}
.. autofunction:: my_project.api.compact_function
```
````

Render a class with grouped content regions and member entries:

````myst
```{eval-rst}
.. autoclass:: my_project.api.LayoutDemo
   :members:
```
````

## Live demos

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
| `gal_signature_show_annotations` | `True` | Shows `name: type` in expanded folded signatures when type data is available |

## Shared helper surface

- `build_api_card_entry()` builds the shared inner `api-*` shell for
  section-card consumers such as FastMCP.
- `build_api_summary_section()` wraps summary and index tables in the shared
  `api-summary` region.

## CSS classes

| Class | Element | Purpose |
|-------|---------|---------|
| `api-container` | `<dl>` | Managed autodoc shell |
| `api-header` | `<dt>` | Signature row shell |
| `api-content` | `<dd>` | Description/content shell |
| `api-layout` | `<div>` | Header split between left and right |
| `api-layout-left` | `<div>` | Signature text, custom disclosure, permalink |
| `api-layout-right` | `<div>` | Badge container and source link |
| `api-signature` | `<div>` | Compact signature row |
| `api-link` | `<a>` | Managed permalink in the left layout |
| `api-badge-container` | `<span>` | Wrapper for badge group output |
| `api-source-link` | `<span>` | Wrapper for the `[source]` link |
| `api-description` | `<div>` | Wraps paragraphs, notes, examples |
| `api-parameters` | `<div>` | Wraps field lists (Parameters, Returns) |
| `api-footer` | `<div>` | Wraps nested method/attribute entries |
| `gal-region` | `<div>` | Compatibility alias on content sections |
| `gal-region--narrative` | `<div>` | Compatibility alias on narrative sections |
| `gal-region--fields` | `<div>` | Compatibility alias on parameter sections |
| `gal-region--members` | `<div>` | Compatibility alias on footer/member sections |
| `gal-fold` | `<details>` | Disclosure wrapper for large sections |
| `gal-fold-summary` | `<summary>` | Click target showing field count |

```{package-reference} sphinx-autodoc-layout
```
