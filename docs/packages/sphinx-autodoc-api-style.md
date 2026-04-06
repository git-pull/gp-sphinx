(sphinx-autodoc-api-style)=

# sphinx-autodoc-api-style

{bdg-warning-line}`Alpha` {bdg-link-secondary-line}`GitHub <https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-api-style>` {bdg-link-secondary-line}`PyPI <https://pypi.org/project/sphinx-autodoc-api-style/>`

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

## How it works

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

No special directives are needed — existing `.. autofunction::`,
`.. autoclass::`, `.. automodule::` directives automatically receive badges.

## Live demo

```{py:module} gas_demo_api
```

### Functions

```{eval-rst}
.. autofunction:: gas_demo_api.demo_function
```

```{eval-rst}
.. autofunction:: gas_demo_api.demo_async_function
```

```{eval-rst}
.. autofunction:: gas_demo_api.demo_deprecated_function
```

### Module data

```{eval-rst}
.. autodata:: gas_demo_api.DEMO_CONSTANT
```

### Exceptions

```{eval-rst}
.. autoexception:: gas_demo_api.DemoError
```

### Classes

```{eval-rst}
.. autoclass:: gas_demo_api.DemoClass
   :members:
   :undoc-members:
```

### Abstract base classes

```{eval-rst}
.. autoclass:: gas_demo_api.DemoAbstractBase
   :members:
```

## Badge reference

### Type badges

| Object type | CSS class | Color |
|-------------|-----------|-------|
| `function` | `gas-type-function` | Blue |
| `class` | `gas-type-class` | Indigo |
| `method` | `gas-type-method` | Cyan |
| `property` | `gas-type-property` | Teal |
| `attribute` | `gas-type-attribute` | Slate |
| `data` | `gas-type-data` | Grey |
| `exception` | `gas-type-exception` | Rose |

### Modifier badges

| Modifier | CSS class | Style |
|----------|-----------|-------|
| `async` | `gas-mod-async` | Purple outlined |
| `classmethod` | `gas-mod-classmethod` | Amber outlined |
| `staticmethod` | `gas-mod-staticmethod` | Grey outlined |
| `abstract` | `gas-mod-abstract` | Indigo outlined |
| `final` | `gas-mod-final` | Emerald outlined |
| `deprecated` | `gas-deprecated` | Red/grey outlined |

## CSS prefix

All CSS classes use the `gas-` prefix (**g**p-sphinx **a**pi **s**tyle) to avoid
collision with `spf-` (sphinx pytest fixtures) or other extensions.

```{package-reference} sphinx-autodoc-api-style
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-api-style) · [PyPI](https://pypi.org/project/sphinx-autodoc-api-style/)
