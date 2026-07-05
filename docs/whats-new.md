(whats-new)=

# What's new

gp-sphinx includes a unified **autodoc design system**: eight major
advancements that shape how the documentation stack works. See the
{doc}`gallery` for a visual showcase.

## New packages

Two new foundational packages form the core of the rendering pipeline:

- {doc}`sphinx-ux-autodoc-layout <packages/sphinx-ux-autodoc-layout/index>` — componentized
  autodoc output with semantic regions, parameter folding, managed signatures,
  and card containers.
- {doc}`sphinx-autodoc-typehints-gp <packages/sphinx-autodoc-typehints-gp/index>` — single-package
  replacement for `sphinx-autodoc-typehints` and `sphinx.ext.napoleon`.
  Resolves annotations statically at build time with no monkey-patching.

## Unified badge system

All badge colours have been consolidated into
{doc}`sphinx-ux-badges <packages/sphinx-ux-badges/index>`.  Every
downstream package references `SAB.*` constants instead of maintaining its
own colour classes — one palette, thirty-plus colour variants, full
light/dark theming.

## Shared layout stack

The autodoc extensions
({doc}`api-style <packages/sphinx-autodoc-api-style/index>`,
{doc}`argparse <packages/sphinx-autodoc-argparse/index>`,
{doc}`docutils <packages/sphinx-autodoc-docutils/index>`,
{doc}`fastmcp <packages/sphinx-autodoc-fastmcp/index>`,
{doc}`pytest-fixtures <packages/sphinx-autodoc-pytest-fixtures/index>`,
{doc}`sphinx <packages/sphinx-autodoc-sphinx/index>`)
now all share the same layout, badge, and typehint infrastructure.  A
change in the foundational layout package propagates instantly and
consistently.

## argparse Sphinx domain

{doc}`sphinx-autodoc-argparse <packages/sphinx-autodoc-argparse/index>` now
ships a real {py:class}`sphinx.domains.Domain` subclass.  Programs, options, subcommands,
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

## sphinx-vite-builder: Vite + pnpm orchestration end-to-end

{doc}`sphinx-vite-builder <packages/sphinx-vite-builder/index>` consolidates
the workspace's Vite story into a single package with three orthogonal
activation paths sharing one async-subprocess core:

- **PEP 517 build backend** — `build-backend =
  "sphinx_vite_builder.build"` runs `pnpm exec vite build` before
  delegating wheel/sdist construction to `hatchling.build`. End users
  who `pip install` from PyPI get a wheel with the static tree
  pre-baked at release time and never need pnpm or Node.
- **Hatchling build hook** — `[tool.hatch.build.hooks.vite]`
  composes with any other hatchling hook stack, so projects already
  using `build-backend = "hatchling.build"` can adopt Vite without
  swapping the backend.
- **Sphinx extension** — `extensions = ["sphinx_vite_builder"]` in
  `conf.py` auto-orchestrates Vite during docs builds: a one-shot
  `pnpm exec vite build` for plain `sphinx-build`, a long-running
  `pnpm exec vite build --watch` child process under
  `sphinx-autobuild`, with graceful SIGTERM → SIGKILL teardown on
  signal / `atexit`.

The whole product is the **wheel-vs-source asymmetry**: a `web/`
directory triggers strict orchestration with fast-fail diagnostics
(`PnpmMissingError`, `NodeModulesInstallError`, `ViteFailedError`,
each carrying a copy-pasteable hint), while an absent `web/` (the
unpacked-sdist case) short-circuits cleanly so wheels published to
PyPI need zero toolchain on the consumer side. Errors are
self-healing in CI: detected providers (GitHub Actions, CircleCI,
Azure Pipelines, GitLab CI) get the right setup recipe inlined into
the error message.

The legacy `gp-sphinx-vite` extension has been retired in favour of
`sphinx-vite-builder`; consumers using
`merge_sphinx_config(vite_orchestration=True)` continue to work
without code changes.
