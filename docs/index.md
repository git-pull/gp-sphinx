(index)=

# gp-sphinx

Shared Sphinx documentation platform for [git-pull](https://github.com/git-pull) projects.

::::{grid} 1 1 2 3
:gutter: 2 2 3 3

:::{grid-item-card} Quickstart
:link: quickstart
:link-type: doc
Install and get started in minutes.
:::

:::{grid-item-card} Packages
:link: packages/index
:link-type: doc
Five workspace packages — coordinator, extensions, and theme.
:::

:::{grid-item-card} Configuration
:link: configuration
:link-type: doc
Parameter reference for `merge_sphinx_config()` and shared defaults.
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

```{toctree}
:hidden:

quickstart
configuration
packages/index
api
project/index
history
```
