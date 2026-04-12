(sphinx-autodoc-api-style)=

# sphinx-autodoc-api-style

```{sab-package-meta} sphinx-autodoc-api-style
```

:::{admonition} Alpha
:class: warning

Rendered output is stable. The Python API, CSS class names, and Sphinx
config value names may change without a major version bump. Pin your
dependency to a specific version range in production.
:::

Sphinx extension that adds type and modifier badges to standard Python domain
entries (functions, classes, methods, properties, attributes, data,
exceptions). Mirrors the badge system from
{doc}`sphinx-autodoc-pytest-fixtures` so API pages and fixture pages share a
consistent visual language.

```console
$ pip install sphinx-autodoc-api-style
```

## Features

- **Type badges** (rightmost): `function`, `class`, `method`, `property`,
  `attribute`, `data`, `exception` — each with a distinct color
- **Modifier badges** (left of type): `async`, `classmethod`, `staticmethod`,
  `abstract`, `final`, `deprecated`
- **Card containers**: bordered cards with secondary-background headers
- **Dark mode**: full light/dark theming via CSS custom properties
- **Accessibility**: keyboard-focusable badges with tooltip popups
- **Non-invasive**: hooks into `doctree-resolved` without replacing directives

## Downstream `conf.py`

Add `sphinx_autodoc_api_style` to your Sphinx extensions. With `gp-sphinx`,
use `extra_extensions`:

```python
conf = merge_sphinx_config(
    project="my-project",
    version="1.0.0",
    copyright="2026, Your Name",
    source_repository="https://github.com/your-org/my-project/",
    extra_extensions=["sphinx_autodoc_api_style"],
)
```

Or without `merge_sphinx_config`:

```python
extensions = ["sphinx_autodoc_api_style"]
```

`sphinx_autodoc_api_style` automatically registers `sphinx_ux_badges` and
`sphinx_autodoc_layout` via `app.setup_extension()`. You do not need to add
them separately to your `extensions` list.

## Working usage examples

No special directives are needed — existing `.. autofunction::`,
`.. autoclass::`, `.. automodule::` directives automatically receive badges.

Render one function:

````myst
```{eval-rst}
.. autofunction:: my_project.api.demo_function
```
````

Render one class and its members:

````myst
```{eval-rst}
.. autoclass:: my_project.api.DemoClass
   :members:
```
````

## Live demos

```{py:module} gp_demo_api
```

### Functions

```{eval-rst}
.. autofunction:: gp_demo_api.demo_function
```

```{eval-rst}
.. autofunction:: gp_demo_api.demo_async_function
```

```{eval-rst}
.. autofunction:: gp_demo_api.demo_deprecated_function
```

### Module data

```{eval-rst}
.. autodata:: gp_demo_api.DEMO_CONSTANT
```

### Exceptions

```{eval-rst}
.. autoexception:: gp_demo_api.DemoError
```

### Classes

```{eval-rst}
.. autoclass:: gp_demo_api.DemoClass
   :members:
   :undoc-members:
```

### Abstract base classes

```{eval-rst}
.. autoclass:: gp_demo_api.DemoAbstractBase
   :members:
```

## Badge reference

All badge classes are drawn from the shared `sphinx_ux_badges.SAB` palette.
This extension uses:

| Object type | `SAB` constant | CSS class |
|---|---|---|
| `function` | `SAB.TYPE_FUNCTION` | `sab-type-function` |
| `class` | `SAB.TYPE_CLASS` | `sab-type-class` |
| `method` | `SAB.TYPE_METHOD` | `sab-type-method` |
| `property` | `SAB.TYPE_PROPERTY` | `sab-type-property` |
| `attribute` | `SAB.TYPE_ATTRIBUTE` | `sab-type-attribute` |
| `data` | `SAB.TYPE_DATA` | `sab-type-data` |
| `exception` | `SAB.TYPE_EXCEPTION` | `sab-type-exception` |

| Modifier | `SAB` constant | CSS class |
|---|---|---|
| `async` | `SAB.MOD_ASYNC` | `sab-mod-async` |
| `classmethod` | `SAB.MOD_CLASSMETHOD` | `sab-mod-classmethod` |
| `staticmethod` | `SAB.MOD_STATICMETHOD` | `sab-mod-staticmethod` |
| `abstract` | `SAB.MOD_ABSTRACT` | `sab-mod-abstract` |
| `final` | `SAB.MOD_FINAL` | `sab-mod-final` |
| `deprecated` | `SAB.STATE_DEPRECATED` | `sab-state-deprecated` |

See {doc}`sphinx-ux-badges` for the full shared palette.

## CSS prefix

All badge CSS classes use the `sab-` prefix from {doc}`sphinx-ux-badges`.
Layout card classes (borders, headers, field-list rules) are local to this package
and use `dl.py-*` and `.api-*` selectors.

```{package-reference} sphinx-autodoc-api-style
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-api-style) · [PyPI](https://pypi.org/project/sphinx-autodoc-api-style/)
