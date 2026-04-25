# gp-sphinx

```{gp-sphinx-package-meta} gp-sphinx
```

:::{admonition} Alpha
:class: warning

Rendered output is stable. The Python API, CSS class names, and Sphinx
config value names may change without a major version bump. Pin your
dependency to a specific version range in production.
:::

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
- Auto-computed `issue_url_tpl` and theme source-repository wiring from `source_repository`.
- Auto-computed SEO values when `docs_url` is set: `ogp_site_url`, `ogp_site_name`, `ogp_image` for {doc}`sphinx-gp-opengraph`, plus `site_url` and `sitemap_url_scheme` for {doc}`sphinx-gp-sitemap`. See {ref}`from-docs_url` for the canonical mapping.
- A `setup(app)` hook that registers `js/spa-nav.js` and removes `tabs.js` after HTML builds.
- Support for appending {py:mod}`sphinx:sphinx.ext.linkcode` automatically when `linkcode_resolve` is supplied in `**overrides`.

See {doc}`/configuration` for the complete parameter reference and every shared `DEFAULT_*` constant.

## SEO emission for free

`sphinx_gp_opengraph` and `sphinx_gp_sitemap` are members of
{py:data}`~gp_sphinx.defaults.DEFAULT_EXTENSIONS`, so every project
that calls `merge_sphinx_config()` loads them automatically. Passing
`docs_url=` is the only step required for default SEO emission —
gp-sphinx fills in the upstream config keys both extensions need.
Per-package details live on the {doc}`sphinx-gp-opengraph` and
{doc}`sphinx-gp-sitemap` pages.

:::{admonition} Live example
This site is built with `gp-sphinx`, using the same integration pattern shown
above. See
[docs/conf.py](https://github.com/git-pull/gp-sphinx/blob/main/docs/conf.py)
for the exact coordinator call.
:::

```{package-reference} gp-sphinx
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/gp-sphinx) · [PyPI](https://pypi.org/project/gp-sphinx/)
