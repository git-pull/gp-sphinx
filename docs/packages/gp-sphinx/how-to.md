(gp-sphinx-how-to)=

# How to

Use the coordinator when a downstream project wants the shared theme,
extensions, fonts, SEO defaults, and workspace conventions from one
`docs/conf.py` call.

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
- Auto-computed `issue_url_tpl` and theme source-repository wiring from `source_repository`.
- Auto-computed SEO values when `docs_url` is set: `ogp_site_url`, `ogp_site_name`, `ogp_image` for {doc}`/packages/sphinx-gp-opengraph/index`, plus `site_url` and `sitemap_url_scheme` for {doc}`/packages/sphinx-gp-sitemap/index`. See {ref}`from-docs_url` for the canonical mapping.
- A `setup(app)` hook that registers `js/spa-nav.js` and removes `tabs.js` after HTML builds.
- Support for appending {py:mod}`sphinx:sphinx.ext.linkcode` automatically when `linkcode_resolve` is supplied in `**overrides`.

See {doc}`/configuration` for the complete parameter reference and every shared `DEFAULT_*` constant.

## SEO emission for free

`sphinx_gp_opengraph` and `sphinx_gp_sitemap` are members of
{py:data}`~gp_sphinx.defaults.DEFAULT_EXTENSIONS`, so every project that calls
{py:func}`~gp_sphinx.config.merge_sphinx_config` loads them automatically.
Passing `docs_url=` is the only step required for default SEO emission —
gp-sphinx fills in the upstream config keys both extensions need.
Per-package details live on the {doc}`/packages/sphinx-gp-opengraph/index` and
{doc}`/packages/sphinx-gp-sitemap/index` pages.

:::{admonition} Live example
This site is built with `gp-sphinx`, using the same integration pattern shown
above. See
[docs/conf.py](https://github.com/git-pull/gp-sphinx/blob/main/docs/conf.py)
for the exact coordinator call.
:::

```{package-reference} gp-sphinx
```
