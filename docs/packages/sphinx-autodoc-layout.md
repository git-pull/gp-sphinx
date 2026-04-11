(sphinx-autodoc-layout)=

# sphinx-autodoc-layout

```{sab-package-meta} sphinx-autodoc-layout
```

:::{admonition} Alpha
:class: warning

Rendered output is stable. The Python API, CSS class names, and Sphinx
config value names may change without a major version bump. Pin your
dependency to a specific version range in production.
:::

Wraps contiguous `desc_content` runs into semantic `api_region` nodes
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

## Pipeline position

Hooks `doctree-resolved` at priority **600**, after `sphinx-autodoc-api-style`
at 500. Consumes the `api_slot` nodes that producer packages inject into
`desc_signature` during earlier transforms, and composes them into the final
`api-layout-right` subcomponent (badges, source link, permalink).

The extension also overrides Sphinx's built-in `desc_signature` HTML visitor
(`app.add_node(addnodes.desc_signature, override=True, ...)`). This is a
deliberate platform decision: taking ownership of signature rendering allows
the `api-link` permalink to be placed inside the managed layout rather than
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
    extra_extensions=["sphinx_autodoc_layout"],
    api_layout_enabled=True,
    api_collapsed_threshold=10,
)
```

Or without `merge_sphinx_config`:

```python
extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_layout"]
api_layout_enabled = True
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

### Class with members (regions + fold)

```{eval-rst}
.. autoclass:: gal_demo_api.LayoutDemo
   :members:
```

The class above renders with:

- **narrative** region (class docstring)
- **fields** region with fold (13 parameters > threshold of 10)
- **members** region (connect, execute, close methods)

### Small function (no fold)

```{eval-rst}
.. autofunction:: gal_demo_api.compact_function
```

## Configuration

| Setting | Default | Meaning |
|---------|---------|---------|
| `api_layout_enabled` | `False` | Enables the transform |
| `api_fold_parameters` | `True` | Folds large field-list sections |
| `api_collapsed_threshold` | `10` | Minimum field count before folding |
| `api_signature_show_annotations` | `True` | Shows `name: type` in expanded folded signatures when type data is available |

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
| `api-region` | `<div>` | Compatibility alias on content sections |
| `api-region--narrative` | `<div>` | Compatibility alias on narrative sections |
| `api-region--fields` | `<div>` | Compatibility alias on parameter sections |
| `api-region--members` | `<div>` | Compatibility alias on footer/member sections |
| `api-fold` | `<details>` | Disclosure wrapper for large sections |
| `api-fold-summary` | `<summary>` | Click target showing field count |

## API reference

```{eval-rst}
.. autofunction:: sphinx_autodoc_layout.build_api_card_entry

.. autofunction:: sphinx_autodoc_layout.build_api_summary_section

.. autofunction:: sphinx_autodoc_layout.build_api_table_section

.. autofunction:: sphinx_autodoc_layout.build_api_facts_section
```

```{package-reference} sphinx-autodoc-layout
```
