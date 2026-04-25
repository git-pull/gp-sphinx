# sphinx-gp-opengraph

OpenGraph meta-tag emission for Sphinx — a drop-in replacement for
[`sphinxext-opengraph`](https://github.com/sphinx-doc/sphinxext-opengraph)
that ships every `ogp_*` config key the upstream supports, minus the
matplotlib-based social-card generator. No image-rendering dependencies,
no system-fontconfig surprises.

Part of the [gp-sphinx](https://github.com/git-pull/gp-sphinx)
documentation platform.

## Install

```console
$ pip install sphinx-gp-opengraph
```

When you depend on gp-sphinx, this extension is already loaded — see
[Auto-derived values](#auto-derived-values-when-used-with-gp-sphinx)
below.

## Minimum viable conf.py

```python
extensions = [
    "sphinx_gp_opengraph",
]
```

```python
ogp_site_url = "https://example.com/"
```

```python
ogp_image = "_static/og-default.png"
```

A 1200×630 PNG works on Slack, Facebook, LinkedIn, and X/Twitter
unfurlers. With these three values set, every page rendered by an
HTML-family builder gains `og:title`, `og:type`, `og:url`,
`og:site_name`, `og:description`, `og:image`, and `og:image:alt`. A
matching `<meta name="description">` is emitted when the page does not
already define one.

## Auto-derived values when used with gp-sphinx

Projects that build through {py:func}`gp_sphinx.config.merge_sphinx_config`
do not need to set `ogp_site_url`, `ogp_site_name`, or `ogp_image`
manually. Pass `docs_url=` to `merge_sphinx_config()` and gp-sphinx
fills all three from that one value. See [the sphinx-gp-opengraph package
page](../../docs/packages/sphinx-gp-opengraph.md) for the integration story
and [`configuration.md`](../../docs/configuration.md#from-docs_url)
for the canonical mapping table.

## Per-page overrides

Set front-matter fields to override the site-wide defaults on a single
page. MyST syntax shown; reST field-list syntax behaves the same way.

```markdown
---
ogp_description_length: 160
og:image: _static/og/this-page.png
og:image:alt: A tailored hero for this page
---

# Page title

Body paragraph that becomes og:description.
```

| Field | Effect |
| --- | --- |
| `og:image` | Replace the site-default image for this page |
| `og:image:alt` | Replace the alt text for this page |
| `ogp_description_length` | Override the description-length cap for this page |
| `ogp_disable: true` | Skip OpenGraph emission entirely on this page |

Any other `og:*` field-list entry is forwarded to the page head verbatim,
so `og:type`, `og:audio`, etc. work without code changes.

## Config-key reference

Every key is registered with `rebuild="html"` and the indicated default.
Per-page front-matter wins over these site-wide values.

| Key | Type | Default | Purpose |
| --- | --- | --- | --- |
| `ogp_site_url` | `str` | `""` | Site base URL; required for absolute `og:url` (auto-derived under gp-sphinx) |
| `ogp_canonical_url` | `str` | `""` | Separate canonical URL; falls back to `ogp_site_url` when empty |
| `ogp_description_length` | `int` | `200` | Truncation cap for `og:description` |
| `ogp_image` | `str \| None` | `None` | Site-default OG image (auto-derived under gp-sphinx) |
| `ogp_image_alt` | `str \| bool \| None` | `None` | Alt text; falls back to `og:site_name`, then `og:title`. `False` suppresses the alt tag |
| `ogp_use_first_image` | `bool` | `False` | Use the first in-page image as `og:image` when no override is set |
| `ogp_type` | `str` | `"website"` | Value of the `og:type` tag |
| `ogp_site_name` | `str \| bool \| None` | `None` (→ `project`) | `False` suppresses the `og:site_name` tag |
| `ogp_social_cards` | `dict \| None` | `None` | Accepted-but-ignored — see [Migration](#migration-from-sphinxext-opengraph) |
| `ogp_custom_meta_tags` | `list[str]` | `()` | Raw `<meta>` tags emitted verbatim — use this for Twitter cards |
| `ogp_enable_meta_description` | `bool` | `True` | Emit a matching `<meta name="description">` |

### Twitter cards

sphinx-gp-opengraph does not register a separate `twitter_*` namespace;
crawlers fall back to `og:*` for most fields. Append explicit Twitter
markup through `ogp_custom_meta_tags` when you need it:

```python
ogp_custom_meta_tags = [
    '<meta name="twitter:card" content="summary_large_image" />',
    '<meta property="og:image:width" content="1200" />',
    '<meta property="og:image:height" content="630" />',
]
```

## Migration from `sphinxext-opengraph`

Configuration is drop-in compatible — every `ogp_*` key is registered
with the same name, type, and default — with one behavioural change:

- **`ogp_social_cards` is accepted but ignored.** sphinx-gp-opengraph does not
  bundle the matplotlib-based card generator the upstream ships. Setting
  the value emits one `WARNING` at `config-inited`:

  ```text
  sphinx-gp-opengraph: ogp_social_cards ignored — sphinx-gp-opengraph ships no card generator; use a static PNG via ogp_image (site default) or per-page 'og:image' frontmatter
  ```

  Grep your build log for `ogp_social_cards ignored` to find this
  warning.

The recommended replacement is one static PNG per page. Drop them under
`_static/og/` and point the per-page `og:image` field-list entry at
each one. The downstream UX is the same as upstream's auto-generated
cards — just explicit, and with no build-time dependency on matplotlib
or PIL.

```text
docs/
├── _static/
│   └── og/
│       ├── default.png
│       ├── quickstart.png
│       └── reference.png
├── quickstart.md
└── reference.md
```

```markdown
---
og:image: _static/og/quickstart.png
---

# Quickstart
```

## See also

- [sphinx-gp-sitemap](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-sitemap)
  — companion package for `sitemap.xml` emission
- [gp-sphinx](https://github.com/git-pull/gp-sphinx) — the umbrella
  docs platform; auto-derives `ogp_site_url`, `ogp_site_name`, and
  `ogp_image` from a single `docs_url` argument
- [sphinx-gp-opengraph package page](https://gp-sphinx.git-pull.com/packages/sphinx-gp-opengraph/)
  — integration story, event hooks, and how-it-works
