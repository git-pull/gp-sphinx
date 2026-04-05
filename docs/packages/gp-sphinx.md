# gp-sphinx

{bdg-warning-line}`Alpha` {bdg-link-secondary-line}`GitHub <https://github.com/git-pull/gp-sphinx/tree/main/packages/gp-sphinx>` {bdg-link-secondary-line}`PyPI <https://pypi.org/project/gp-sphinx/>`

Shared configuration coordinator for Sphinx projects. {py:func}`~gp_sphinx.config.merge_sphinx_config`
builds a complete `conf.py` namespace from the workspace defaults and leaves
per-project overrides in one place.

```console
$ pip install gp-sphinx
```

```console
$ uv add gp-sphinx
```

## Downstream `conf.py`

```python
from __future__ import annotations

from gp_sphinx.config import merge_sphinx_config

import my_project

conf = merge_sphinx_config(
    project="my-project",
    version=my_project.__version__,
    copyright="2026, Your Name",
    source_repository="https://github.com/your-org/my-project/",
    docs_url="https://my-project.example.com/",
    intersphinx_mapping={
        "py": ("https://docs.python.org/3", None),
    },
)
globals().update(conf)
```

## What it injects

- Shared extension defaults, theme defaults, fonts, MyST, napoleon, copybutton, and rediraffe settings.
- Auto-computed values like `issue_url_tpl`, `ogp_site_url`, `ogp_site_name`, and `ogp_image` when repository and docs URLs are provided.
- A `setup(app)` hook that registers `js/spa-nav.js` and removes `tabs.js` after HTML builds.
- Support for appending {py:mod}`sphinx:sphinx.ext.linkcode` automatically when `linkcode_resolve` is supplied in `**overrides`.

See {doc}`/configuration` for the complete parameter reference and every shared `DEFAULT_*` constant.

:::{admonition} Live example
This site is built with `gp-sphinx`, using the same integration pattern shown
above. See
[docs/conf.py](https://github.com/git-pull/gp-sphinx/blob/main/docs/conf.py)
for the exact coordinator call.
:::

```{package-reference} gp-sphinx
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/gp-sphinx)
