(architecture)=

# Architecture

Workspace packages organized in tiers.  Lower layers never depend on
higher ones — autodoc extensions consume shared infrastructure, and the
presentation layer wires everything together for downstream projects.

The sidebar groups these packages into navigation buckets (Domain Packages,
UX, Utils, Internal) — a reader-facing grouping that is orthogonal to the
dependency-ordered tier map below.

## Tier 1: Shared infrastructure

The rendering pipeline that every autodoc extension consumes:

::::{grid} 1 1 3 3
:gutter: 2

:::{grid-item-card} sphinx-ux-badges
:link: packages/sphinx-ux-badges/index
:link-type: doc

Badge primitives, colour palette, and CSS infrastructure.
All badge colours live in one place (`SAB.*` constants).
:::

:::{grid-item-card} sphinx-ux-autodoc-layout
:link: packages/sphinx-ux-autodoc-layout
:link-type: doc

Structural presenter for `api-*` entry components.
Parameter folding, managed signatures, card regions.
:::

:::{grid-item-card} sphinx-autodoc-typehints-gp
:link: packages/sphinx-autodoc-typehints-gp
:link-type: doc

Annotation normalization and type rendering.
Replaces `sphinx-autodoc-typehints` + `sphinx.ext.napoleon`.
:::

::::

## Tier 2: Autodoc extensions

Domain-specific [autodoc extensions](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html)
that consume Tier 1 and add project-specific rendering logic. Each
ships directives that generate documentation from a particular
source-construct family:

::::{grid} 1 1 2 3
:gutter: 2

:::{grid-item-card} sphinx-autodoc-api-style
:link: packages/sphinx-autodoc-api-style/index
:link-type: doc

**Subject**: standard Python.
**Directives**: `autofunction`, `autoclass`, `automodule`.
:::

:::{grid-item-card} sphinx-autodoc-argparse
:link: packages/sphinx-autodoc-argparse
:link-type: doc

**Subject**: argparse parsers — programs, options, subcommands, positionals.
**Directives**: `argparse` (custom `argparse` domain).
:::

:::{grid-item-card} sphinx-autodoc-docutils
:link: packages/sphinx-autodoc-docutils
:link-type: doc

**Subject**: docutils directives and roles.
**Directives**: `autodirective`, `autorole`.
:::

:::{grid-item-card} sphinx-autodoc-fastmcp
:link: packages/sphinx-autodoc-fastmcp
:link-type: doc

**Subject**: FastMCP tools, prompts, resources.
**Directives**: `fastmcp-tool`, `fastmcp-tool-summary`.
:::

:::{grid-item-card} sphinx-autodoc-pytest-fixtures
:link: packages/sphinx-autodoc-pytest-fixtures
:link-type: doc

**Subject**: pytest fixtures (extends the `py` domain).
**Directives**: `autofixture`, `autofixtures`, `auto-pytest-plugin`.
:::

:::{grid-item-card} sphinx-autodoc-sphinx
:link: packages/sphinx-autodoc-sphinx/index
:link-type: doc

**Subject**: Sphinx config values.
**Directives**: `autoconfigvalue`, `autoconfigvalues`.
:::

::::

Each autodoc extension calls `app.setup_extension()` to auto-register its
infrastructure dependencies — downstream projects only need to add the
package to their `extensions` list.

## Tier 3: Theme and coordinator

| Package | Role |
|---------|------|
| {doc}`gp-sphinx <packages/gp-sphinx>` | Coordinator.  `merge_sphinx_config()` wires up the full stack. |
| {doc}`sphinx-gp-theme <packages/sphinx-gp-theme>` | Furo-based theme with CSS variables and SPA navigation. |
| {doc}`gp-furo-theme <packages/gp-furo-theme>` | Tailwind v4 port of upstream Furo for git-pull projects. |
| {doc}`sphinx-fonts <packages/sphinx-fonts/index>` | IBM Plex via Fontsource — preloaded web fonts. |

## Build tooling

Cross-cutting build utilities that operate outside the docs-build
runtime — one is a [PEP 517](https://peps.python.org/pep-0517/) build
backend invoked when wheels are produced; the other is an opt-in
extension that drives the Vite watcher during `sphinx-autobuild`.
Both let theme authors keep build artefacts (`static/styles/*.css`,
`static/scripts/*.js`) out of VCS while still shipping working wheels
and seamless live-reload during authoring.

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} sphinx-vite-builder
:link: packages/sphinx-vite-builder
:link-type: doc

[PEP 517](https://peps.python.org/pep-0517/) build backend (or
hatchling build hook via `[tool.hatch.build.hooks.vite]`) that runs
`pnpm exec vite build` before delegating wheel/sdist construction to
hatchling. Also a Sphinx extension that auto-orchestrates
`vite build --watch` during `sphinx-autobuild` and one-shot
`vite build` during plain `sphinx-build`.
Source builds error loudly without pnpm/Node; wheels ship turn-key.
**Publishable for use outside this workspace** — any vite + Sphinx
project can adopt either activation path without depending on the
gp-sphinx coordinator.
:::

::::

## How the tiers connect

Every autodoc extension shares the same badge palette, the same
componentized HTML output structure, and the same type annotation
pipeline — so [Python APIs](packages/sphinx-autodoc-api-style/index.md),
[pytest fixtures](packages/sphinx-autodoc-pytest-fixtures.md),
[Sphinx config values](packages/sphinx-autodoc-sphinx/index.md),
[docutils directives](packages/sphinx-autodoc-docutils.md), and
[FastMCP tools](packages/sphinx-autodoc-fastmcp.md) all look like
they belong together.

This is the **one autodoc design system** principle: a change to the shared
infrastructure propagates instantly and consistently across every autodoc
extension in the workspace.
