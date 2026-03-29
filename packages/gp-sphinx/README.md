# gp-sphinx &middot; [![Python Package](https://img.shields.io/pypi/v/gp-sphinx.svg)](https://pypi.org/project/gp-sphinx/) [![License](https://img.shields.io/github/license/git-pull/gp-sphinx.svg)](https://github.com/git-pull/gp-sphinx/blob/master/LICENSE)

Shared Sphinx documentation platform for [git-pull](https://github.com/git-pull) projects.

Consolidates duplicated docs configuration, extensions, theme settings, and workarounds from 14+ repositories into a single reusable package.

## Install

```console
$ pip install gp-sphinx
```

```console
$ uv add gp-sphinx
```

## Usage

Replace ~300 lines of duplicated `docs/conf.py` with ~10 lines:

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

## Features

- `merge_sphinx_config()` API for shared defaults with per-project overrides
- Shared extension list (autodoc, intersphinx, myst_parser, sphinx_design, etc.)
- Shared Furo theme configuration (CSS variables, fonts, sidebar, footer)
- Bundled workarounds (tabs.js removal, spa-nav.js injection)
- Shared font configuration (IBM Plex via Fontsource)

## More information

- Documentation: <https://gp-sphinx.git-pull.com>
- Source: <https://github.com/git-pull/gp-sphinx>
- Changelog: <https://github.com/git-pull/gp-sphinx/blob/master/CHANGES>
- Issues: <https://github.com/git-pull/gp-sphinx/issues>
- PyPI: <https://pypi.org/project/gp-sphinx/>
- License: [MIT](https://github.com/git-pull/gp-sphinx/blob/master/LICENSE)
