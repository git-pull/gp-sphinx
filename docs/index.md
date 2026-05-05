(index)=

# gp-sphinx

Integrated autodoc design system for [git-pull](https://github.com/git-pull) Sphinx projects.

::::{grid} 1 1 2 3
:gutter: 2 2 3 3

:::{grid-item-card} What's New
:link: whats-new
:link-type: doc
The unified autodoc design system — seven major advancements.
:::

:::{grid-item-card} Gallery
:link: gallery
:link-type: doc
Visual showcase of the autodoc design system in action.
:::

:::{grid-item-card} Architecture
:link: architecture
:link-type: doc
Split into common libraries, build utils, autodoc extensions, and UX.
:::

:::{grid-item-card} Quickstart
:link: quickstart
:link-type: doc
Install and get started in minutes.
:::

:::{grid-item-card} Packages
:link: packages/index
:link-type: doc
Coordinator, autodoc extensions, build utils, UX components, and theme.
:::

:::{grid-item-card} Configuration
:link: configuration
:link-type: doc
Parameter reference for {py:func}`~gp_sphinx.config.merge_sphinx_config` and shared defaults.
:::

::::

## Install

```console
$ pip install gp-sphinx
```

```console
$ uv add gp-sphinx
```

## At a glance

Replace ~300 lines of duplicated `docs/conf.py` with ~10 lines:

```python
from gp_sphinx.config import merge_sphinx_config

conf = merge_sphinx_config(
    project="my-project",
    version="1.0.0",
    copyright="2026, Tony Narlock",
    source_repository="https://github.com/git-pull/my-project/",
)
globals().update(conf)
```

## What you get

Out of the box, {py:func}`~gp_sphinx.config.merge_sphinx_config` activates:

- **Unified badge system** — type and modifier badges for functions, classes, fixtures, tools
- **Componentized layout** — card containers, parameter folding, managed signatures
- **Clean type hints** — simplified annotations with cross-referenced links
- **Autodoc extensions** — Python API, pytest fixtures, FastMCP tools, docutils, Sphinx config
- **IBM Plex fonts** — professional typography with preloaded web fonts
- **Dark mode** — full light/dark theming via CSS custom properties

See the {doc}`gallery` to see these in action.

```{toctree}
:hidden:

whats-new
gallery
architecture
quickstart
configuration
packages/index
api
project/index
history
```

```{toctree}
:caption: Domain Packages
:hidden:

packages/sphinx-autodoc-api-style/index
packages/sphinx-autodoc-argparse/index
packages/sphinx-autodoc-docutils/index
packages/sphinx-autodoc-fastmcp/index
packages/sphinx-autodoc-pytest-fixtures/index
packages/sphinx-autodoc-sphinx/index
```

```{toctree}
:caption: UX
:hidden:

packages/sphinx-fonts/index
packages/sphinx-ux-autodoc-layout
packages/sphinx-ux-badges/index
```

```{toctree}
:caption: Utils
:hidden:

packages/sphinx-autodoc-typehints-gp/index
```

```{toctree}
:caption: Internal
:hidden:

packages/gp-sphinx
packages/sphinx-gp-theme
packages/gp-furo-theme
```

```{toctree}
:caption: Build utils
:hidden:

packages/sphinx-vite-builder
```

```{toctree}
:caption: SEO
:hidden:

packages/sphinx-gp-opengraph
packages/sphinx-gp-sitemap
```
