(sphinx-ux-autodoc-layout)=

# sphinx-ux-autodoc-layout

```{gp-sphinx-package-meta} sphinx-ux-autodoc-layout
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
$ pip install sphinx-ux-autodoc-layout
```

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

```{py:module} api_demo_layout
```

### Class with members (regions + fold)

```{eval-rst}
.. autoclass:: api_demo_layout.LayoutDemo
   :members:
```

The class above renders with:

- **narrative** region (class docstring)
- **fields** region with fold (13 parameters > threshold of 10)
- **members** region (connect, execute, close methods)

### Small function (no fold)

```{eval-rst}
.. autofunction:: api_demo_layout.compact_function
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
  `gp-sphinx-api-summary` region.

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
