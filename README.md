# gp-sphinx &middot; [![Python Package](https://img.shields.io/pypi/v/gp-sphinx.svg)](https://pypi.org/project/gp-sphinx/) [![License](https://img.shields.io/github/license/git-pull/gp-sphinx.svg)](https://github.com/git-pull/gp-sphinx/blob/main/LICENSE)

Integrated autodoc design system for Sphinx.  Twelve packages in three tiers
that replace ~300 lines of duplicated `docs/conf.py` with ~10 lines and
produce beautiful, consistent API documentation.

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

- **Componentized layouts** (`sphinx-autodoc-layout`) — card containers, parameter folding, managed signatures
- **Clean type hints** (`sphinx-autodoc-typehints-gp`) — simplified annotations with cross-referenced links, replacing `sphinx-autodoc-typehints` and `sphinx.ext.napoleon`
- **Unified badge system** (`sphinx-autodoc-badges`) — type and modifier badges with a shared colour palette
- **Five domain autodocumenters** — Python API, pytest fixtures, FastMCP tools, docutils directives, Sphinx config values
- **IBM Plex fonts** via Fontsource with preloaded web fonts
- **Full dark mode** theming via CSS custom properties

See the [Gallery](https://gp-sphinx.git-pull.com/gallery.html) for live demos of every component.

## Three-tier architecture

The workspace is organized into three tiers — lower layers never depend on higher ones:

- **Shared infrastructure**: `sphinx-autodoc-badges`, `sphinx-autodoc-layout`, `sphinx-autodoc-typehints-gp`
- **Domain packages**: `sphinx-autodoc-api-style`, `sphinx-autodoc-docutils`, `sphinx-autodoc-fastmcp`, `sphinx-autodoc-pytest-fixtures`, `sphinx-autodoc-sphinx`
- **Theme and coordinator**: `gp-sphinx`, `sphinx-gp-theme`, `sphinx-fonts`, `sphinx-autodoc-argparse`

See the [Architecture](https://gp-sphinx.git-pull.com/architecture.html) page for the full package map.

## More information

- Documentation: <https://gp-sphinx.git-pull.com>
- Source: <https://github.com/git-pull/gp-sphinx>
- Changelog: <https://github.com/git-pull/gp-sphinx/blob/main/CHANGES>
- Issues: <https://github.com/git-pull/gp-sphinx/issues>
- PyPI: <https://pypi.org/project/gp-sphinx/>
- License: [MIT](https://github.com/git-pull/gp-sphinx/blob/main/LICENSE)
