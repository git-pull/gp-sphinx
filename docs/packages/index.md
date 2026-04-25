# Packages

Fourteen workspace packages in four tiers.

**Shared infrastructure** — the rendering pipeline that all domain packages consume:
- `sphinx-ux-badges` — badge primitives and colour palette
- `sphinx-ux-autodoc-layout` — structural presenter for `api-*` entry components
- `sphinx-autodoc-typehints-gp` — annotation normalization and type rendering

**Domain packages** — domain-specific autodoc extensions.  Each either
ships its own Sphinx domain or extends an existing one with new
directives, roles, and per-domain indices:
- `sphinx-autodoc-api-style`, `sphinx-autodoc-argparse`,
  `sphinx-autodoc-docutils`, `sphinx-autodoc-fastmcp`,
  `sphinx-autodoc-pytest-fixtures`, `sphinx-autodoc-sphinx`

**Theme and coordinator** — shared Sphinx configuration and presentation
assets:
- `gp-sphinx`, `sphinx-gp-theme`, `sphinx-fonts`

**SEO** — meta-tag and crawlability extensions auto-loaded by
`gp-sphinx` when `docs_url` is set:
- `sphinx-gp-opengraph`, `sphinx-gp-sitemap`

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
