(whats-new)=

# What's new

The `autodoc-improvements` branch introduces a unified **autodoc design
system** — eight major advancements that transform how the documentation
stack works.  See the {doc}`gallery` for a visual showcase.

## New packages

Two new foundational packages form the core of the rendering pipeline:

- {doc}`sphinx-ux-autodoc-layout <packages/sphinx-ux-autodoc-layout>` — componentized
  autodoc output with semantic regions, parameter folding, managed signatures,
  and card containers.
- {doc}`sphinx-autodoc-typehints-gp <packages/sphinx-autodoc-typehints-gp>` — single-package
  replacement for `sphinx-autodoc-typehints` and `sphinx.ext.napoleon`.
  Resolves annotations statically at build time with no monkey-patching.

## Unified badge system

All badge colours have been consolidated into
{doc}`sphinx-ux-badges <packages/sphinx-ux-badges>`.  Every
downstream package references `SAB.*` constants instead of maintaining its
own colour classes — one palette, thirty-plus colour variants, full
light/dark theming.

## Shared layout stack

The autodoc extensions
({doc}`api-style <packages/sphinx-autodoc-api-style>`,
{doc}`argparse <packages/sphinx-autodoc-argparse>`,
{doc}`docutils <packages/sphinx-autodoc-docutils>`,
{doc}`fastmcp <packages/sphinx-autodoc-fastmcp>`,
{doc}`pytest-fixtures <packages/sphinx-autodoc-pytest-fixtures>`,
{doc}`sphinx <packages/sphinx-autodoc-sphinx>`)
now all share the same layout, badge, and typehint infrastructure.  A
change in the foundational layout package propagates instantly and
consistently.

## argparse Sphinx domain

{doc}`sphinx-autodoc-argparse <packages/sphinx-autodoc-argparse>` now
ships a real Sphinx `Domain` subclass.  Programs, options, subcommands,
and positional arguments are individually addressable via
`:argparse:program:`, `:argparse:option:`, `:argparse:subcommand:`, and
`:argparse:positional:` xref roles.  Two auto-generated indices —
`argparse-programsindex` (alphabetised programs) and
`argparse-optionsindex` (options grouped by program) — give a workspace
overview.  `:option:` / `std:cmdoption` continues to resolve for
intersphinx consumers.

## Three-tier package organization

The workspace has been restructured into a clear {doc}`three-tier
architecture <architecture>`: shared infrastructure at the bottom, domain
packages in the middle, and the theme/coordinator at the top.  Lower
layers never depend on higher ones.

## 9.5x test speedup

Shared Sphinx scenario caching via `tests/_sphinx_scenarios.py` reduced
full-suite runtime from ~40 s to ~4.2 s for 916 tests.  Builds are keyed
by a SHA-256 content-hash digest and reused across all tests that share
the same scenario.

## Snapshot testing

[Syrupy](https://github.com/toptal/syrupy) snapshot assertions lock in
doctree structure, rendered HTML, and warning output.  Three custom
fixtures normalize build-path churn and docutils version noise so that
snapshots stay stable across environments.

## Doctree-first testing

The majority of tests now operate directly on the docutils doctree —
constructing `nodes.*` objects in Python — instead of running full Sphinx
builds.  This makes tests faster, more precise, and easier to debug.
