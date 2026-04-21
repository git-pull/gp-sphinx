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

Or — when part of a gp-sphinx site — you already have it (gp-sphinx
pulls this in by default).

## Usage

Enable in your `docs/conf.py`:

```python
extensions = [
    "sphinx_gp_sitemap",
]

site_url = "https://example.com/"
```

A `sitemap.xml` is written to the HTML output directory on every build.
One `<url>` element per built page; auto-skipped for the index of the
`dirhtml` builder (emitted as the bare base URL, not `index/`).

## Config reference

| Key | Type | Default | Purpose |
|---|---|---|---|
| `site_url` | `str \| None` | `None` | Base URL. Falls back to `html_baseurl` |
| `sitemap_url_scheme` | `str` | `"{lang}{version}{link}"` | Per-URL template |
| `sitemap_locales` | `list \| None` | `[]` (auto-detect) | `hreflang` alternates |
| `sitemap_filename` | `str` | `"sitemap.xml"` | Output filename |
| `sitemap_excludes` | `list[str]` | `[]` | fnmatch patterns to skip |
| `sitemap_show_lastmod` | `bool` | `False` | Include `<lastmod>` from git |
| `sitemap_indent` | `int` | `0` | XML indent width (0 = minified) |

## Multi-language sites

When `sitemap_locales` is set (or auto-detected from `locale_dirs`),
each `<url>` gains `<xhtml:link rel="alternate" hreflang="...">`
entries for every locale:

```python
sitemap_locales = ["de", "fr", "ja"]
```

Use `sitemap_locales = [None]` to explicitly suppress hreflang
alternates.

## Excluding pages

```python
sitemap_excludes = [
    "draft/*",
    "internal-*",
]
```

Patterns match the `sitemap_link` (relative page URL after the builder
applies its suffix) via `fnmatch`.

## `lastmod` from git

```python
sitemap_show_lastmod = True
```

Loads `sphinx-last-updated-by-git` transparently and emits `<lastmod>`
per page based on the file's latest commit timestamp. Silently
disables itself (with a warning) when the extension is not installed.

## Differences from `sphinx-sitemap`

Configuration is **drop-in compatible** with upstream — switching to
`sphinx-gp-sitemap` does not require any conf.py changes.

Implementation changes behind the scenes:

- Collected links stored in `env.temp_data["sphinx_gp_sitemap_links"]` as a
  plain `list[tuple[str, str | None]]` — no `multiprocessing.Queue`.
  Sphinx joins parallel workers before `build-finished` fires, so the
  Queue machinery was over-engineered.
- Builder-kind detection uses `app.builder.name == "dirhtml"` —
  no `env.is_directory_builder` monkey-patch.
- `html_baseurl` re-registration uses
  `contextlib.suppress(ExtensionError)` rather than a bare
  `except BaseException`.
- All `add_config_value` calls use `types=frozenset({...})` uniform.

## See also

- [sphinx-gp-opengraph](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-opengraph) —
  companion package for OpenGraph / Twitter meta-tag emission
- [gp-sphinx](https://github.com/git-pull/gp-sphinx) — the umbrella
  docs platform that auto-wires this extension's `site_url` from
  `docs_url`
