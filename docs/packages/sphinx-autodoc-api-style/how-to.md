(sphinx-autodoc-api-style-how-to)=

# How to

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

Or without {py:func}`~gp_sphinx.config.merge_sphinx_config`:

```python
extensions = ["sphinx_autodoc_api_style"]
```

`sphinx_autodoc_api_style` automatically registers `sphinx_ux_badges` and
`sphinx_ux_autodoc_layout` via
{py:meth}`~sphinx.application.Sphinx.setup_extension`. You do not need to
add them separately to your `extensions` list.

## CSS prefix

All badge CSS classes use the `gp-sphinx-badge` namespace from
{doc}`/packages/sphinx-ux-badges/index`. Layout card rules are local to this
package and target Sphinx's `dl.py-*` selectors plus shared `gp-sphinx-api-*`
wrappers.

```{package-reference} sphinx-autodoc-api-style
```
