# gp-sphinx

{bdg-warning-line}`Alpha` {bdg-success}`coordinator`

Configuration coordinator for shared Sphinx documentation infrastructure.
A single `merge_sphinx_config()` call builds a complete Sphinx namespace from
shared defaults — extensions, theme, fonts, autodoc settings, copybutton,
MyST, and more.

```console
$ pip install gp-sphinx
```

```console
$ uv add gp-sphinx
```

## Usage

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

That single call configures 13 extensions, the sphinx-gptheme Furo child
theme, IBM Plex fonts via sphinx-fonts, copybutton with regex prompt
stripping, MyST with colon fences and linkify, intersphinx, opengraph,
rediraffe, and napoleon.

:::{admonition} Self-documenting
This docs site is built by gp-sphinx. See
[docs/conf.py](https://github.com/git-pull/gp-sphinx/blob/master/docs/conf.py)
— it uses the same `merge_sphinx_config()` pattern described here.
:::

See {doc}`/configuration` for the full parameter reference and shared
defaults.

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/master/packages/gp-sphinx)
