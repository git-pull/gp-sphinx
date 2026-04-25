# sphinx-gp-sitemap

Sitemap generator for Sphinx — a drop-in replacement for
[`sphinx-sitemap`](https://github.com/jdillard/sphinx-sitemap) updated
to Sphinx 8.1+ idioms. Same `sitemap_*` configuration surface, no
`multiprocessing.Queue`, and a soft (lazy-loaded) dependency on
[`sphinx-last-updated-by-git`](https://github.com/mgeier/sphinx-last-updated-by-git)
that activates only when `sitemap_show_lastmod = True`.

Part of the [gp-sphinx](https://github.com/git-pull/gp-sphinx)
documentation platform.

## Install

```console
$ pip install sphinx-gp-sitemap
```

When you depend on gp-sphinx, this extension is already loaded — see
[Auto-derived values](#auto-derived-values-when-used-with-gp-sphinx)
below. The full config-key reference is auto-generated on the
[package docs page](https://gp-sphinx.git-pull.com/packages/sphinx-gp-sitemap/)
from the live `app.add_config_value()` registrations.

## Minimum viable conf.py

```python
extensions = [
    "sphinx_gp_sitemap",
]
```

```python
site_url = "https://example.com/"
```

After every HTML-family build, `sitemap.xml` is written to the output
directory. One `<url>` element per page; the index of the `dirhtml`
builder is emitted as the bare base URL (not `index/`). When
`site_url` is unset and `html_baseurl` is also unset, sitemap
emission is skipped silently — the notice is logged at INFO, not
WARNING, so `-W` strict builds do not fail on undeployed projects.

## Auto-derived values when used with gp-sphinx

Projects that build through {py:func}`gp_sphinx.config.merge_sphinx_config`
do not need to set `site_url` or `sitemap_url_scheme` manually. Pass
`docs_url=` to `merge_sphinx_config()` and gp-sphinx fills both:

- `site_url` is normalized to end in `/`.
- `sitemap_url_scheme` is set to `"{link}"` — flat, no language or
  version path segment — because git-pull.com sites deploy at the
  project root.

See the [sphinx-gp-sitemap package
page](../../docs/packages/sphinx-gp-sitemap.md) for the integration story
and [`configuration.md`](../../docs/configuration.md#from-docs_url)
for the canonical mapping table.

## Builder support

| Builder | URL shape | Notes |
| --- | --- | --- |
| `html` | `…/<page>.html` (or `…<html_file_suffix>`) | Honors `html_file_suffix` for `.htm` mirrors |
| `dirhtml` | `…/<page>/` | Site index emitted as the bare `site_url`, not `…/index/` |

Other builders (`text`, `latex`, `singlehtml`, …) are unaffected — they
do not fire `html-page-context`, so no sitemap is written.

## Multi-language sites

When `sitemap_locales` is set or auto-detected from `locale_dirs`,
each `<url>` gains `<xhtml:link rel="alternate" hreflang="…">`
entries for every locale. Underscores in locale codes are rewritten
to hyphens for IANA compatibility (`pt_BR` → `pt-BR`).

```python
sitemap_locales = ["de", "fr", "ja"]
```

Use `sitemap_locales = [None]` to explicitly suppress hreflang
alternates — useful when `locale_dirs` is populated for translation
workflows that do not produce hreflang-eligible deploys.

## Excluding pages

```python
sitemap_excludes = [
    "draft/*",
    "internal-*",
]
```

Patterns match the `sitemap_link` (the relative page URL after the
builder applies its suffix) via `fnmatch`. The patterns run after
suffix application, so `draft/index.html` and `draft/index/` both
match `draft/*` regardless of builder.

## `lastmod` from git

```python
sitemap_show_lastmod = True
```

The first time `config-inited` fires with this flag set, sphinx-gp-sitemap
runs `app.setup_extension("sphinx_last_updated_by_git")` to load
[`sphinx-last-updated-by-git`](https://github.com/mgeier/sphinx-last-updated-by-git)
on demand. Per-page `<lastmod>` values come from each source file's
latest commit timestamp. If the supporting extension is not
installed, sphinx-gp-sitemap warns once and disables `sitemap_show_lastmod`
for the rest of the build — `<lastmod>` is simply omitted.

## Differences from `sphinx-sitemap`

Configuration is drop-in compatible — every `sitemap_*` key is
registered with the same name, type, and default. Behaviourally the
package is the same except for one explicit trade-off:

- **Parallel writes are not declared safe.** Collected links live in
  `env.temp_data["sphinx_gp_sitemap_links"]`, which Sphinx documents as
  per-process state and does not merge across `sphinx-build -j N`
  workers. sphinx-gp-sitemap therefore advertises `parallel_read_safe` only.
  Sites that need parallel writes should run a separate non-parallel
  pass for sitemap generation, or upstream the env-merge work to
  this package.

The other differences are implementation modernizations (no
`multiprocessing.Queue`, public `app.builder.name == "dirhtml"`
detection rather than monkey-patching, `contextlib.suppress(ExtensionError)`
around the optional `html_baseurl` re-registration). These do not
change the configuration surface.

## See also

- [sphinx-gp-opengraph](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-opengraph)
  — companion package for OpenGraph meta-tag emission
- [gp-sphinx](https://github.com/git-pull/gp-sphinx) — the umbrella
  docs platform; auto-derives `site_url` and `sitemap_url_scheme`
  from a single `docs_url` argument
- [sphinx-gp-sitemap package page](https://gp-sphinx.git-pull.com/packages/sphinx-gp-sitemap/)
  — integration story, event hooks, and the parallel-write trade-off
