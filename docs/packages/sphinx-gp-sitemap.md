(sphinx-gp-sitemap)=

# sphinx-gp-sitemap

```{gp-sphinx-package-meta} sphinx-gp-sitemap
```

:::{admonition} Alpha
:class: warning

Rendered output is stable. The Python API and Sphinx config value names
may change without a major version bump. Pin your dependency to a
specific version range in production.
:::

Sitemap generator for Sphinx. Drop-in replacement for
[`sphinx-sitemap`](https://github.com/jdillard/sphinx-sitemap) with
Sphinx 8.1+ idioms and a parallel-build-safe implementation — no
`multiprocessing.Queue`, no monkey-patched environment attributes.

```console
$ pip install sphinx-gp-sitemap
```

When your docs site depends on `gp-sphinx`, this extension is already
loaded in `DEFAULT_EXTENSIONS` and `site_url` is auto-computed from
`docs_url` (normalized to a trailing slash). No conf.py changes needed.

## What it emits

After every HTML build, a `sitemap.xml` file is written to the output
directory. One `<url>` element per page visited by the
`html-page-context` hook, filtered against `sitemap_excludes`.

- Plain HTML builder: URLs end in `.html` (or the `html_file_suffix`).
- DirectoryHTMLBuilder (`dirhtml`): URLs end in `/`; the site index is
  emitted as the bare base URL rather than `index/`.
- Multi-language: each `<url>` gains `<xhtml:link rel="alternate"
  hreflang="...">` siblings for every locale in `sitemap_locales` (or
  auto-detected from `locale_dirs`).
- With `sitemap_show_lastmod = True`: `<lastmod>` dates from the latest
  git commit per page, via `sphinx-last-updated-by-git`.

## URL templating

`sitemap_url_scheme` controls per-URL composition; default
`"{lang}{version}{link}"`. A gp-sphinx site with Sphinx's `language =
"en"` and `version = "1.2.3"` produces URLs like
`https://example.com/en/1.2.3/quickstart/`.

Override to drop the version segment:

```python
sitemap_url_scheme = "{lang}{link}"
```

## Migration from `sphinx-sitemap`

`conf.py` files using the upstream extension keep working — every
`sitemap_*` key is registered with identical semantics.

Implementation modernizations happen behind the scenes:

- Collected links on `env.temp_data["sphinx_gp_sitemap_links"]` as a plain
  `list` (no `multiprocessing.Queue`).
- `app.builder.name == "dirhtml"` (no `env.is_directory_builder`
  monkey-patch).
- Narrow `contextlib.suppress(ExtensionError)` around the optional
  `html_baseurl` re-registration (no bare `except BaseException`).
- All `add_config_value` calls use `types=frozenset({...})`.

## Package reference

```{package-reference} sphinx-gp-sitemap
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-sitemap) · [PyPI](https://pypi.org/project/sphinx-gp-sitemap/)
