# sphinx-autodoc-badges

{bdg-warning-line}`Alpha` {bdg-link-secondary-line}`GitHub <https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-badges>` {bdg-link-secondary-line}`PyPI <https://pypi.org/project/sphinx-autodoc-badges/>`

Shared badge node and CSS infrastructure for Sphinx autodoc extensions.

Provides `BadgeNode`, HTML visitors, and builder helpers that
`sphinx-autodoc-api-style`, `sphinx-autodoc-pytest-fixtures`, and
`sphinx-autodoc-fastmcp` share instead of reimplementing badges independently.

## Features

- **`BadgeNode(nodes.inline)`** -- MRO-safe custom node that falls back to
  `visit_inline` in text/LaTeX/man builders
- **Shared CSS** -- base metrics, icon-only, inline-icon, TOC dot compression,
  context-aware sizing, heading flex alignment
- **CSS custom properties** -- plugins set `--sab-bg` / `--sab-fg` / `--sab-border`;
  projects override in `custom.css` for palette variants
- **Builder API** -- `build_badge()`, `build_badge_group()`, `build_toolbar()`

## Usage

Extensions depend on this package and call `app.setup_extension("sphinx_autodoc_badges")`
in their `setup()` function.
