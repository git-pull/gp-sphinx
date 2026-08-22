# AGENTS.md

gp-sphinx is a uv workspace of Sphinx documentation-platform packages: a
coordinator (`merge_sphinx_config()`), autodoc extensions, a Furo-based
theme, and the SEO/build tooling that ships around them for the
git-pull fleet.

Follow the conventions already in the tree, and keep a change scoped to
what was asked for.

## What is here

| Path | What it is |
| --- | --- |
| `packages/gp-sphinx/` | Coordinator: `merge_sphinx_config()`, `DEFAULT_EXTENSIONS` |
| `packages/sphinx-gp-theme/`, `packages/gp-furo-theme/` | Furo-based theme; `gp-furo-theme/web/` is the Vite/CSS source |
| `packages/gp-furo-tokens/` | Design tokens (TS, pnpm-only, excluded from the uv workspace) |
| `packages/sphinx-autodoc-*/` | Autodoc extensions: api-style, argparse, docutils, fastmcp, pytest-fixtures, sphinx, typehints-gp |
| `packages/sphinx-ux-*/`, `sphinx-fonts/` | Shared layout, badges, fonts |
| `packages/sphinx-gp-{opengraph,sitemap,llms}/` | SEO, auto-loaded when `docs_url` is set |
| `packages/sphinx-gp-{mermaid,highlighting}/` | Diagrams and syntax highlighting |
| `packages/sphinx-vite-builder/` | PEP 517 build backend + Sphinx extension; own `AGENTS.md` |
| `src/gp_sphinx_workspace/` | Bootstrap package for the workspace root |
| `docs/` | This project's own docs site — its own flagship consumer |
| `tests/` | pytest suite: `_sphinx_scenarios.py`, `_snapshots.py`, `docs/` policy tests |
| `scripts/ci/` | Version bump and release-metadata tooling |
| `CHANGES` | The changelog |

## Which policy applies

- Documentation, user-facing text, `CHANGES`, commit messages,
  docstrings, and source comments:
  [.github/WRITING.md](.github/WRITING.md)
- Environment, the gates, tests, documentation builds, releases, and
  pull requests: [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md)

Each of those is the single home for its subject. Where a rule seems to
be stated twice, the file listed above is the one that governs.

## Change discipline

- Make the smallest coherent change that solves the verified problem;
  keep unrelated cleanup out of it.
- Reuse an existing file, helper, API, or test before adding a new one.
- Add a file only for a durable boundary — a distinct responsibility,
  independent reuse, or splitting an oversized module — not for a
  single-use helper or a one-line re-export.
- Add a test for every user-visible behaviour change, and a `CHANGES`
  entry for every change to the public API, CLI, configuration, or
  output.
- A passing gate is evidence only once it has been shown capable of
  failing. Pair a new test with a deliberate break that proves it bites.

`pytest --doctest-modules` collects doctests from `.py` files under
`testpaths` only: `packages/*/src`, `docs/_ext/`, and `tests/`. A
`>>> ` prompt on a Markdown page under `docs/` or in `README.md` does
not run — see
[WRITING.md](.github/WRITING.md#documented-examples-that-run). All
publishable packages share one lockstep version, bumped with
`just bump-version <version>`.

## References

- Changelog: [CHANGES](CHANGES)
- Docs: <https://gp-sphinx.git-pull.com>
- Source: <https://github.com/git-pull/gp-sphinx>
