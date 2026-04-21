# sphinx-gp-sitemap

Sitemap generator for Sphinx — drop-in replacement for
[`sphinx-sitemap`](https://github.com/jdillard/sphinx-sitemap) with
Sphinx 8.1+ idioms and a parallel-build-safe implementation (no
`multiprocessing.Queue`).

Part of the [gp-sphinx](https://github.com/git-pull/gp-sphinx) documentation
platform.

## Install

```console
$ pip install sphinx-gp-sitemap
```

## Usage

Enable in your `docs/conf.py`:

```python
extensions = [
    "sphinx_gp_sitemap",
]

site_url = "https://example.com/"
```

A `sitemap.xml` is written to your HTML output directory after each
build.

Scaffolding — full extension arrives in follow-up commits.
