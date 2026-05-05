# Packages

The workspace ships independently-installable Sphinx packages
organized by family. Each package has its own page; the
{ref}`grid below <all-workspace-packages>` auto-enumerates the full
set as the workspace evolves.

[`gp-sphinx`](gp-sphinx.md) is the umbrella entry point — its
`merge_sphinx_config()` wires up the full stack for downstream
projects in ~10 lines of `conf.py`. Every other package is opt-in
and independently installable.

## Common libraries

The rendering pipeline every autodoc extension consumes:

- [`sphinx-ux-badges`](sphinx-ux-badges/index.md) — badge primitives and colour palette
- [`sphinx-ux-autodoc-layout`](sphinx-ux-autodoc-layout.md) — structural presenter for `api-*` entry components
- [`sphinx-autodoc-typehints-gp`](sphinx-autodoc-typehints-gp/index.md) — annotation normalization and type rendering
- [`sphinx-fonts`](sphinx-fonts/index.md) — IBM Plex font preloading

## Autodoc extensions

Domain-specific [autodoc extensions](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html) — each adds directives that generate documentation from a particular source-construct family (Python APIs, argparse parsers, pytest fixtures, etc.):

- [`sphinx-autodoc-api-style`](sphinx-autodoc-api-style/index.md) — Python API rendering style
- [`sphinx-autodoc-argparse`](sphinx-autodoc-argparse/index.md) — argparse parsers + subcommands
- [`sphinx-autodoc-docutils`](sphinx-autodoc-docutils/index.md) — docutils directives + nodes
- [`sphinx-autodoc-fastmcp`](sphinx-autodoc-fastmcp/index.md) — FastMCP tools, prompts, resources
- [`sphinx-autodoc-pytest-fixtures`](sphinx-autodoc-pytest-fixtures/index.md) — pytest fixtures
- [`sphinx-autodoc-sphinx`](sphinx-autodoc-sphinx/index.md) — Sphinx config values

## Build utils

[PEP 517](https://peps.python.org/pep-0517/) backends and orchestration helpers for theme asset pipelines:

- [`sphinx-vite-builder`](sphinx-vite-builder.md) — [PEP 517](https://peps.python.org/pep-0517/) backend + Sphinx extension that runs Vite via pnpm

## Theme and coordinator

Shared Sphinx configuration and presentation assets:

- [`gp-sphinx`](gp-sphinx.md) — umbrella coordinator (`merge_sphinx_config()`)
- [`sphinx-gp-theme`](sphinx-gp-theme.md) — Furo child theme with the gp-sphinx default palette
- [`gp-furo-theme`](gp-furo-theme.md) — Tailwind v4 port of upstream Furo for git-pull projects

## SEO

Meta-tag and crawlability extensions auto-loaded by `gp-sphinx` when `docs_url` is set:

- [`sphinx-gp-opengraph`](sphinx-gp-opengraph.md) — Open Graph + Twitter Card meta tags
- [`sphinx-gp-sitemap`](sphinx-gp-sitemap.md) — `sitemap.xml` for crawl indexing

## Design philosophy

Together, the common libraries provide **one autodoc design system**: every autodoc extension shares the same badge palette, the same componentized HTML output structure, and the same static type annotation pipeline — so Python APIs, pytest fixtures, Sphinx config values, docutils directives, and FastMCP tools all look like they belong together.

(all-workspace-packages)=
## All workspace packages

```{workspace-package-grid}
```
