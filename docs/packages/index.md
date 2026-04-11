# Packages

Twelve workspace packages in three tiers.

**Shared infrastructure** — the rendering pipeline that all domain packages consume:
- `sphinx-autodoc-badges` — badge primitives and colour palette
- `sphinx-autodoc-layout` — structural presenter for `api-*` entry components
- `sphinx-autodoc-typehints-gp` — annotation normalization and type rendering

**Autodoc domain packages** — domain-specific autodoc extensions:
- `sphinx-autodoc-api-style`, `sphinx-autodoc-docutils`, `sphinx-autodoc-fastmcp`,
  `sphinx-autodoc-pytest-fixtures`, `sphinx-autodoc-sphinx`

**Theme, fonts, and CLI** — shared Sphinx configuration and assets:
- `gp-sphinx`, `sphinx-gp-theme`, `sphinx-fonts`, `sphinx-autodoc-argparse`

`gp-sphinx` is the umbrella entry point: `merge_sphinx_config()` wires up the
full stack for downstream projects.

Each domain package is independently installable but automatically loads its
infrastructure dependencies.

Together, the shared infrastructure provides **one autodoc design system**:
every domain package shares the same badge palette, the same componentized
HTML output structure, and the same static type annotation pipeline — so
Python APIs, pytest fixtures, Sphinx config values, docutils directives,
and FastMCP tools all look like they belong together.

```{workspace-package-grid}
```

```{toctree}
:caption: Shared Infrastructure
:hidden:

sphinx-autodoc-badges
sphinx-autodoc-layout
sphinx-autodoc-typehints-gp
```

```{toctree}
:caption: Domain Packages
:hidden:

sphinx-autodoc-api-style
sphinx-autodoc-docutils
sphinx-autodoc-fastmcp
sphinx-autodoc-pytest-fixtures
sphinx-autodoc-sphinx
```

```{toctree}
:caption: Theme, Fonts & CLI
:hidden:

gp-sphinx
sphinx-gp-theme
sphinx-fonts
sphinx-autodoc-argparse
```
