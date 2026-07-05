(sphinx-autodoc-api-style-reference)=

# API Reference

## Badge reference

All badge classes are drawn from the shared
{py:class}`~sphinx_ux_badges._css.SAB` palette. This extension uses:

| Object type | {py:class}`~sphinx_ux_badges._css.SAB` constant | CSS class |
|---|---|---|
| `function` | {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_FUNCTION` | `gp-sphinx-badge--type-function` |
| `class` | {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_CLASS` | `gp-sphinx-badge--type-class` |
| `method` | {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_METHOD` | `gp-sphinx-badge--type-method` |
| `property` | {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_PROPERTY` | `gp-sphinx-badge--type-property` |
| `attribute` | {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_ATTRIBUTE` | `gp-sphinx-badge--type-attribute` |
| `data` | {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_DATA` | `gp-sphinx-badge--type-data` |
| `exception` | {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_EXCEPTION` | `gp-sphinx-badge--type-exception` |

| Modifier | {py:class}`~sphinx_ux_badges._css.SAB` constant | CSS class |
|---|---|---|
| `async` | {py:attr}`~sphinx_ux_badges._css.SAB.MOD_ASYNC` | `gp-sphinx-badge--mod-async` |
| `classmethod` | {py:attr}`~sphinx_ux_badges._css.SAB.MOD_CLASSMETHOD` | `gp-sphinx-badge--mod-classmethod` |
| `staticmethod` | {py:attr}`~sphinx_ux_badges._css.SAB.MOD_STATICMETHOD` | `gp-sphinx-badge--mod-staticmethod` |
| `abstract` | {py:attr}`~sphinx_ux_badges._css.SAB.MOD_ABSTRACT` | `gp-sphinx-badge--mod-abstract` |
| `final` | {py:attr}`~sphinx_ux_badges._css.SAB.MOD_FINAL` | `gp-sphinx-badge--mod-final` |
| `deprecated` | {py:attr}`~sphinx_ux_badges._css.SAB.STATE_DEPRECATED` | `gp-sphinx-badge--state-deprecated` |

See {doc}`/packages/sphinx-ux-badges/index` for the full shared palette.

## Extension entry point

```{eval-rst}
.. autofunction:: sphinx_autodoc_api_style.setup
```
