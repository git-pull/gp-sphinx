# Phase 0: `gp_sphinx` -- Shared Sphinx Platform

> [Back to Overview](00-overview.md) | Previous: [Furo Analysis](01-furo-analysis.md) | Next: [Phase 1 -- Astro Bridge](03-phase-1-astro-bridge.md)

**Duration**: 1-2 weeks | **Risk**: Very low | **Status**: Mandatory

## Goal

Consolidate duplicated docs infrastructure from 14+ repositories into a single shared Python package: `gp_sphinx` (PyPI: `gp-sphinx`).

This phase has zero risk, immediate payoff, and is a prerequisite for every subsequent phase. **Do this first regardless of any Astro decision.**

## What Goes in the Package

### Shared Extensions

The extension list is identical across all 14 projects:

```python
# gp_sphinx/defaults.py
DEFAULT_EXTENSIONS = [
    "sphinx.ext.autodoc",
    "sphinx_fonts",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinx.ext.todo",
    "sphinx.ext.napoleon",
    "sphinx.ext.linkcode",
    "sphinx_inline_tabs",
    "sphinx_copybutton",
    "sphinxext.opengraph",
    "sphinxext.rediraffe",
    "sphinx_design",
    "myst_parser",
    "linkify_issues",
]
```

### Shared Theme Options

```python
# gp_sphinx/defaults.py
DEFAULT_THEME_OPTIONS = {
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "",  # Set per-project
            "html": '<svg>...</svg>',
            "class": "",
        },
    ],
    "source_repository": "",  # Set per-project
    "source_branch": "master",
    "source_directory": "docs/",
}
```

### Shared MyST Config

```python
DEFAULT_MYST_HEADING_ANCHORS = 4
DEFAULT_MYST_EXTENSIONS = [
    "colon_fence",
    "substitution",
    "replacements",
    "strikethrough",
    "linkify",
]
```

### Shared Font Config

```python
DEFAULT_FONT_FAMILIES = {
    "IBM Plex Sans": [
        {"weight": 400, "style": "normal"},
        {"weight": 500, "style": "normal"},
        {"weight": 600, "style": "normal"},
        {"weight": 700, "style": "normal"},
    ],
    "IBM Plex Mono": [
        {"weight": 400, "style": "normal"},
        {"weight": 600, "style": "normal"},
    ],
}
```

### Shared Workarounds

The `tabs.js` removal + `spa-nav.js` injection hack, currently duplicated in every `conf.py` `setup()` function.

## The `merge_sphinx_config()` API

Projects are not 100% identical. Some use `argparse_exemplar`, some use `sphinx_click`, some have custom extensions. The shared package must support per-project overrides without abandoning the shared base.

```python
# gp_sphinx/config.py
from __future__ import annotations

import typing as t


def merge_sphinx_config(
    *,
    project: str,
    version: str,
    copyright: str,
    extensions: list[str] | None = None,
    extra_extensions: list[str] | None = None,
    remove_extensions: list[str] | None = None,
    theme_options: dict[str, t.Any] | None = None,
    source_repository: str | None = None,
    source_branch: str = "master",
    light_logo: str | None = None,
    dark_logo: str | None = None,
    intersphinx_mapping: dict[str, tuple[str, str | None]] | None = None,
    **overrides: t.Any,
) -> dict[str, t.Any]:
    """Build a complete Sphinx conf namespace from shared defaults + per-project overrides.

    Parameters
    ----------
    project : str
        Sphinx project name.
    version : str
        Project version string.
    copyright : str
        Copyright string.
    extensions : list[str] | None
        Replace the default extension list entirely. Usually not needed.
    extra_extensions : list[str] | None
        Add extensions to the defaults (e.g., ["argparse_exemplar"]).
    remove_extensions : list[str] | None
        Remove specific defaults (e.g., ["sphinx_design"]).
    theme_options : dict | None
        Deep-merged with default theme options.
    source_repository : str | None
        GitHub repository URL.
    source_branch : str
        Default branch name.
    light_logo : str | None
        Path to light-mode logo.
    dark_logo : str | None
        Path to dark-mode logo.
    intersphinx_mapping : dict | None
        Intersphinx targets.
    **overrides
        Any additional Sphinx config values.

    Returns
    -------
    dict[str, Any]
        Complete Sphinx configuration namespace.
    """
    ...
```

## Before/After: Downstream `conf.py`

### Before (vcspull -- ~300 lines, repeated across 14 repos)

```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_fonts",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    # ... 15 extensions
]
myst_heading_anchors = 4
myst_enable_extensions = ["colon_fence", "substitution", ...]
html_theme = "furo"
html_theme_options = {
    "light_logo": "img/vcspull.svg",
    "dark_logo": "img/vcspull.svg",
    "footer_icons": [...],
    "source_repository": "https://github.com/vcs-python/vcspull/",
    # ... many more
}
# Font config, sidebar config, intersphinx, ...
def setup(app):
    # tabs.js removal hack
    # spa-nav.js injection
    ...
```

### After (~10-15 lines)

```python
"""Sphinx configuration for vcspull documentation."""
from __future__ import annotations

from gp_sphinx.config import merge_sphinx_config

import vcspull

conf = merge_sphinx_config(
    project="vcspull",
    version=vcspull.__version__,
    copyright="2013-2026, Tony Narlock",
    source_repository="https://github.com/vcs-python/vcspull/",
    light_logo="img/vcspull.svg",
    dark_logo="img/vcspull.svg",
    extra_extensions=["argparse_exemplar"],
    intersphinx_mapping={
        "libvcs": ("https://libvcs.git-pull.com/", None),
    },
)
globals().update(conf)
```

## Package Structure

```
gp-sphinx/
  src/
    gp_sphinx/
      __init__.py
      config.py          # merge_sphinx_config() and defaults
      defaults.py        # Extension lists, theme options, MyST config
      assets/            # Shared JS/CSS (spa-nav.js, etc.)
      _compat.py         # Sphinx/docutils version compatibility
  pyproject.toml
  tests/
    test_config.py       # Verify merge logic, override behavior
  README.md
```

## Deliverables

- `gp_sphinx` package published to PyPI as `gp-sphinx`
- `merge_sphinx_config()` API with deep-merge support
- Shared extensions, theme options, MyST config, font config
- Bundled workarounds (`tabs.js` removal, `spa-nav.js`)
- At least 3 projects migrated (vcspull, libvcs, libtmux)

## Success Criteria

- Per-project `docs/conf.py` reduced to ~10-15 lines
- No visual regressions in built docs
- All existing Sphinx extensions still work
- One place to update common docs behavior

## Exit Gate

Proceed to Phase 1 only when the shared package is in use and demonstrably removes real duplication. If shared Sphinx eliminates enough pain, stop here.
