# Packages

Five workspace packages, each independently installable.

::::{grid} 1 1 2 2
:gutter: 2 2 3 3

:::{grid-item-card} gp-sphinx {bdg-warning-line}`Alpha`
:link: gp-sphinx
:link-type: doc
Configuration coordinator. One `merge_sphinx_config()` call replaces
duplicated `docs/conf.py` boilerplate.
:::

:::{grid-item-card} sphinx-autodoc-pytest-fixtures {bdg-warning-line}`Alpha`
:link: sphinx-autodoc-pytest-fixtures
:link-type: doc
Autodocumenter for pytest fixtures with scope badges, dependency
tracking, and usage snippets.
:::

:::{grid-item-card} sphinx-fonts {bdg-success-line}`Beta`
:link: sphinx-fonts
:link-type: doc
Self-hosted web fonts via Fontsource CDN with `@font-face` injection
and preload hints.
:::

:::{grid-item-card} sphinx-gptheme {bdg-success-line}`Beta`
:link: sphinx-gptheme
:link-type: doc
Furo child theme with custom sidebar, SPA navigation, and IBM Plex
typography.
:::

:::{grid-item-card} sphinx-argparse-neo {bdg-success-line}`Beta`
:link: sphinx-argparse-neo
:link-type: doc
Argparse CLI documentation with `.. argparse::` directive and epilog
transformation.
:::

::::

```{toctree}
:hidden:

gp-sphinx
sphinx-autodoc-pytest-fixtures
sphinx-fonts
sphinx-gptheme
sphinx-argparse-neo
```
