# API Reference

Public API for building Sphinx configurations and source link resolvers.

For shared defaults and configuration options, see {doc}`configuration`.

## merge_sphinx_config

```{eval-rst}
.. autofunction:: gp_sphinx.config.merge_sphinx_config
```

## make_linkcode_resolve

```{eval-rst}
.. autofunction:: gp_sphinx.config.make_linkcode_resolve
```

### Wiring into conf.py

Pass the resolver to {py:func}`~gp_sphinx.config.merge_sphinx_config` via `**overrides`.
{py:mod}`sphinx:sphinx.ext.linkcode` is auto-appended to extensions when `linkcode_resolve`
is provided:

```python
import my_project
from gp_sphinx.config import make_linkcode_resolve, merge_sphinx_config

conf = merge_sphinx_config(
    project="my-project",
    version=my_project.__version__,
    copyright="2026, My Name",
    source_repository="https://github.com/my-org/my-project/",
    linkcode_resolve=make_linkcode_resolve(
        my_project,
        "https://github.com/my-org/my-project",
    ),
)
globals().update(conf)
```

## deep_merge

```{eval-rst}
.. autofunction:: gp_sphinx.config.deep_merge
```

## setup

```{eval-rst}
.. autofunction:: gp_sphinx.config.setup
```
