# gp-sphinx &middot; [![Python Package](https://img.shields.io/pypi/v/gp-sphinx.svg)](https://pypi.org/project/gp-sphinx/) [![License](https://img.shields.io/github/license/git-pull/gp-sphinx.svg)](https://github.com/git-pull/gp-sphinx/blob/main/LICENSE)

An integrated autodoc design system for Sphinx that replaces ~300 lines
of duplicated `docs/conf.py` with ~10 lines and produces beautiful,
consistent API documentation.

## Requirements

- Python 3.10+
- Sphinx 8.1+

## Install

```console
$ pip install gp-sphinx
```

```console
$ uv add gp-sphinx
```

## Usage

Replace your `docs/conf.py` with:

```python
"""Sphinx configuration for my-project."""
from __future__ import annotations

from gp_sphinx.config import merge_sphinx_config

import my_project

conf = merge_sphinx_config(
    project="my-project",
    version=my_project.__version__,
    copyright="2026, Tony Narlock",
    source_repository="https://github.com/git-pull/my-project/",
    intersphinx_mapping={
        "py": ("https://docs.python.org/", None),
    },
)
globals().update(conf)
```

## The autodoc design system

Out of the box, `merge_sphinx_config()` activates:

- **Componentized layouts** (`sphinx-ux-autodoc-layout`) — card containers, parameter folding, managed signatures
- **Clean type hints** (`sphinx-autodoc-typehints-gp`) — simplified annotations with cross-referenced links, replacing `sphinx-autodoc-typehints` and `sphinx.ext.napoleon`
- **Unified badge system** (`sphinx-ux-badges`) — type and modifier badges with a shared colour palette
- **Autodoc extensions** — Python API, argparse CLIs, pytest fixtures, FastMCP tools, docutils directives, Sphinx config values
- **IBM Plex fonts** via Fontsource with preloaded web fonts
- **Full dark mode** theming via CSS custom properties

See the [Gallery](https://gp-sphinx.git-pull.com/gallery.html) for live demos of every component.

## Workspace architecture

Lower layers never depend on higher ones:

- **Common libraries** — `sphinx-ux-badges`, `sphinx-ux-autodoc-layout`, `sphinx-autodoc-typehints-gp`, `sphinx-fonts`
- **Autodoc extensions** — `sphinx-autodoc-api-style`, `sphinx-autodoc-argparse`, `sphinx-autodoc-docutils`, `sphinx-autodoc-fastmcp`, `sphinx-autodoc-pytest-fixtures`, `sphinx-autodoc-sphinx`
- **Build utils** — `sphinx-vite-builder` ([PEP 517](https://peps.python.org/pep-0517/) backend + hatchling build hook + Sphinx extension that runs Vite via pnpm; publishable to PyPI for use outside this workspace)
- **Theme and coordinator** — `gp-sphinx`, `sphinx-gp-theme`, `gp-furo-theme`
- **SEO** — `sphinx-gp-opengraph`, `sphinx-gp-sitemap` (auto-loaded by `gp-sphinx` when `docs_url` is set)

See the [Architecture](https://gp-sphinx.git-pull.com/architecture.html)
and [Packages](https://gp-sphinx.git-pull.com/packages/) pages for the
full package map; the docs site auto-enumerates as the workspace grows.

## More information

- Documentation: <https://gp-sphinx.git-pull.com>
- Source: <https://github.com/git-pull/gp-sphinx>
- Changelog: <https://github.com/git-pull/gp-sphinx/blob/main/CHANGES>
- Issues: <https://github.com/git-pull/gp-sphinx/issues>
- PyPI: <https://pypi.org/project/gp-sphinx/>
- License: [MIT](https://github.com/git-pull/gp-sphinx/blob/main/LICENSE)
