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

Sitemap generator for Sphinx. The package registers every `sitemap_*`
config value the upstream
[`sphinx-sitemap`](https://github.com/jdillard/sphinx-sitemap) exposes
and emits the same `sitemap.xml` shape (urlset, hreflang alternates,
optional `<lastmod>`), updated to Sphinx 8.1+ idioms. The hard
dependency on `sphinx-last-updated-by-git` is downgraded to a
soft on-demand load that activates only under
`sitemap_show_lastmod = True`.

For install, the full config-key reference, builder support, locale
rules, and the lastmod / migration story, see the package
[README](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-sitemap#readme).
This page covers integration with gp-sphinx, the emission pipeline,
and the trade-offs.

## Integration with gp-sphinx

`sphinx_gp_sitemap` ships in {py:data}`~gp_sphinx.defaults.DEFAULT_EXTENSIONS`,
so projects that build through {py:func}`~gp_sphinx.config.merge_sphinx_config`
load it automatically. Passing `docs_url=` to that function auto-derives
both URL inputs the extension needs:

| Auto-derived | Source |
| --- | --- |
| `site_url` | `docs_url`, normalized to end in `/` |
| `sitemap_url_scheme` | `"{link}"` (flat — no language or version segment) |

The flat scheme overrides the upstream default of
`"{lang}{version}{link}"` because git-pull.com sites deploy at the
project root, with no language or version directory in the URL space.
Multilingual or version-pinned hosts can still pass an explicit
`sitemap_url_scheme` through `**overrides` — `merge_sphinx_config()`
runs auto-derivation first and overrides last. The canonical mapping
lives in {ref}`from-docs_url`.

## How `sitemap.xml` is built

After every HTML-family build, the extension serializes one `<url>`
element per built page to `sitemap.xml` in the output directory.

1. **Init** — `builder-inited` initializes
   `env.temp_data["sphinx_gp_sitemap_links"]` to an empty list.
2. **Collect** — `html-page-context` fires once per page. The handler
   computes the relative URL using the builder's suffix
   (`html_file_suffix or ".html"` for the `html` builder; `…/` for
   `dirhtml`, with the index emitted as the empty string), drops it
   when any pattern in `sitemap_excludes` matches, and appends a
   `(relative_link, last_updated)` tuple to the list.
3. **Compose** — `build-finished` resolves `site_url` (or
   `html_baseurl` as fallback; if both are unset the build is logged
   at INFO and skipped silently). For each collected link the
   handler formats `site_url + sitemap_url_scheme.format(lang=…,
   version=…, link=…)`. The `lang` segment comes from
   `app.builder.config.language` followed by `/` (empty when no
   language is set); `version` likewise from
   `app.builder.config.version`.
4. **Hreflang** — when `sitemap_locales` resolves to a non-empty list
   (explicit value, or auto-detected sub-directories of every entry
   in `locale_dirs`), each `<url>` gains
   `<xhtml:link rel="alternate" hreflang="…">` siblings. The
   formatter rewrites underscores to hyphens for IANA compatibility
   (`pt_BR` → `pt-BR`). The sentinel `sitemap_locales = [None]`
   suppresses alternates explicitly.
5. **Lastmod** (optional) — when `sitemap_show_lastmod = True`, the
   `config-inited` handler runs
   `app.setup_extension("sphinx_last_updated_by_git")` once at the
   start of the build to lazy-load the supporting extension. If the
   import fails, sphinx-gp-sitemap logs a `WARNING` and disables the flag
   for the rest of the build — `<lastmod>` is omitted but everything
   else still emits.
6. **Serialize** — `xml.etree.ElementTree.write()` produces the file.
   When `sitemap_indent > 0`, `ElementTree.indent()` pretty-prints
   the tree with the configured width. ElementTree handles XML entity
   escaping for the URL text and attribute values automatically.

## Event hooks

```text
config-inited     →  _maybe_enable_git_lastmod  (lazy-load lastmod ext)
builder-inited    →  _init_link_store           (init temp_data list)
html-page-context →  _collect_page_link         (one entry per page)
build-finished    →  _write_sitemap             (XML serialization)
```

All four live in
[`sphinx_gp_sitemap/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-sitemap/src/sphinx_gp_sitemap/__init__.py).
There is no `env-merge-info` or `env-purge-doc` handler — see the
parallel-write trade-off below.

## Trade-offs

**`parallel_write_safe` is not declared.** Sphinx's `temp_data` is
explicitly per-process and is not merged across `sphinx-build -j N`
workers. The upstream `sphinx-sitemap` worked around that with a
`multiprocessing.Manager().Queue`; sphinx-gp-sitemap drops the Queue but
does not yet implement an `env-merge-info`/`env-purge-doc` pair to
preserve parallel-write semantics. Until that work lands, the
extension advertises `parallel_read_safe = True` only. Parallel-read
is the common case (it is what `sphinx-build -j` enables by default
in CI matrices); parallel-write requires the operator to opt in. A
single-process write pass produces a complete sitemap.

**`html_baseurl` is re-registered defensively.** Sphinx core
registers `html_baseurl` on most modern versions, but older trees and
some custom builders skip it. The `setup()` body wraps the
`add_config_value("html_baseurl", …)` call in
`contextlib.suppress(ExtensionError)` so the extension is robust
against either layout. The bare `except BaseException` upstream uses
is replaced by the narrow `ExtensionError` catch.

## Package reference

```{package-reference} sphinx-gp-sitemap
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-sitemap) · [PyPI](https://pypi.org/project/sphinx-gp-sitemap/)
