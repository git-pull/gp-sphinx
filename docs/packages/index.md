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

`gp-sphinx` is the umbrella entry point: `merge_sphinx_config()` wires up the
full stack for downstream projects.

Each domain package is independently installable but automatically loads its
infrastructure dependencies.

```{workspace-package-grid}
```

```{toctree}
:hidden:

sphinx-autodoc-badges
sphinx-autodoc-layout
sphinx-typehints-gp
sphinx-autodoc-api-style
sphinx-autodoc-docutils
sphinx-autodoc-fastmcp
sphinx-autodoc-pytest-fixtures
sphinx-autodoc-sphinx
gp-sphinx
sphinx-gptheme
sphinx-fonts
sphinx-argparse-neo
```
