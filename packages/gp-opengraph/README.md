# gp-opengraph

OpenGraph and Twitter meta-tag emission for Sphinx — drop-in replacement
for [`sphinxext-opengraph`](https://github.com/sphinx-doc/sphinxext-opengraph),
matplotlib-free.

Part of the [gp-sphinx](https://github.com/git-pull/gp-sphinx) documentation
platform.

## Install

```console
$ pip install gp-opengraph
```

## Usage

Enable in your `docs/conf.py`:

```python
extensions = [
    "gp_opengraph",
]

ogp_site_url = "https://example.com/"
ogp_image = "_static/og-default.png"     # 1200×630 recommended
```

Scaffolding — full extension arrives in follow-up commits.
