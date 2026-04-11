# Packages

Eleven workspace packages in three tiers.

**Shared infrastructure** — the rendering pipeline that all domain packages consume:
- `sphinx-autodoc-badges` — badge primitives and colour palette
- `sphinx-autodoc-layout` — structural presenter for `api-*` entry components
- `sphinx-typehints-gp` — annotation normalization and type rendering

**Autodoc domain packages** — domain-specific autodoc extensions:
- `sphinx-autodoc-api-style`, `sphinx-autodoc-docutils`, `sphinx-autodoc-fastmcp`,
  `sphinx-autodoc-pytest-fixtures`, `sphinx-autodoc-sphinx`

**Theme, fonts, and CLI** — shared Sphinx configuration and assets:
- `gp-sphinx`, `sphinx-gptheme`, `sphinx-fonts`, `sphinx-argparse-neo`

Each domain package is independently installable but automatically loads its
infrastructure dependencies.

```{workspace-package-grid}
```

```{toctree}
:hidden:

gp-sphinx
sphinx-autodoc-api-style
sphinx-autodoc-badges
sphinx-autodoc-docutils
sphinx-autodoc-fastmcp
sphinx-autodoc-layout
sphinx-autodoc-sphinx
sphinx-autodoc-pytest-fixtures
sphinx-fonts
sphinx-gptheme
sphinx-argparse-neo
sphinx-typehints-gp
```
