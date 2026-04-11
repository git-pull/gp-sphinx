(architecture)=

# Architecture

Twelve workspace packages in three tiers.  Lower layers never depend on
higher ones — domain packages consume shared infrastructure, and the
presentation layer wires everything together for downstream projects.

## Tier 1: Shared infrastructure

The rendering pipeline that all domain packages consume:

::::{grid} 1 1 3 3
:gutter: 2

:::{grid-item-card} sphinx-autodoc-badges
:link: packages/sphinx-autodoc-badges
:link-type: doc

Badge primitives, colour palette, and CSS infrastructure.
All badge colours live in one place (`SAB.*` constants).
:::

:::{grid-item-card} sphinx-autodoc-layout
:link: packages/sphinx-autodoc-layout
:link-type: doc

Structural presenter for `api-*` entry components.
Parameter folding, managed signatures, card regions.
:::

:::{grid-item-card} sphinx-typehints-gp
:link: packages/sphinx-typehints-gp
:link-type: doc

Annotation normalization and type rendering.
Replaces `sphinx-autodoc-typehints` + `sphinx.ext.napoleon`.
:::

::::

## Tier 2: Domain packages

Domain-specific autodoc extensions that consume Tier 1 and add
project-specific rendering logic:

| Package | Domain | Directives |
|---------|--------|------------|
| {doc}`sphinx-autodoc-api-style <packages/sphinx-autodoc-api-style>` | Standard Python | `autofunction`, `autoclass`, `automodule` |
| {doc}`sphinx-autodoc-docutils <packages/sphinx-autodoc-docutils>` | docutils | `autodirective`, `autorole` |
| {doc}`sphinx-autodoc-fastmcp <packages/sphinx-autodoc-fastmcp>` | FastMCP tools | `fastmcp-tool`, `fastmcp-tool-summary` |
| {doc}`sphinx-autodoc-pytest-fixtures <packages/sphinx-autodoc-pytest-fixtures>` | pytest fixtures | `autofixture`, `autofixture-index` |
| {doc}`sphinx-autodoc-sphinx <packages/sphinx-autodoc-sphinx>` | Sphinx config | `autoconfigvalue`, `autoconfigvalues` |

Each domain package calls `app.setup_extension()` to auto-register its
infrastructure dependencies — downstream projects only need to add the
domain package to their `extensions` list.

## Tier 3: Theme, fonts, and coordinator

| Package | Role |
|---------|------|
| {doc}`gp-sphinx <packages/gp-sphinx>` | Coordinator.  `merge_sphinx_config()` wires up the full stack. |
| {doc}`sphinx-gp-theme <packages/sphinx-gp-theme>` | Furo-based theme with CSS variables and SPA navigation. |
| {doc}`sphinx-fonts <packages/sphinx-fonts>` | IBM Plex via Fontsource — preloaded web fonts. |
| {doc}`sphinx-argparse-neo <packages/sphinx-argparse-neo>` | CLI documentation from `argparse` parsers. |

## How the tiers connect

Every domain package shares the same badge palette, the same componentized
HTML output structure, and the same type annotation pipeline — so Python
APIs, pytest fixtures, Sphinx config values, docutils directives, and
FastMCP tools all look like they belong together.

This is the **one autodoc design system** principle: a change to the shared
infrastructure propagates instantly and consistently across all five
domain packages.
