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

Or — when part of a gp-sphinx site — you already have it (gp-sphinx
pulls this in by default).

## Usage

Enable in your `docs/conf.py`:

```python
extensions = [
    "gp_opengraph",
]

ogp_site_url = "https://example.com/"
ogp_image = "_static/og-default.png"     # 1200×630 recommended for Slack/FB/Twitter
```

That's the minimum. Every page rendered by the HTML-family builders
gains an `og:title`, `og:type`, `og:url`, `og:site_name`,
`og:description`, `og:image`, and `og:image:alt` meta tag.

For Twitter cards, append to `ogp_custom_meta_tags`:

```python
ogp_custom_meta_tags = [
    '<meta name="twitter:card" content="summary_large_image" />',
    '<meta property="og:image:width" content="1200" />',
    '<meta property="og:image:height" content="630" />',
]
```

## Per-page overrides

Override the site-wide defaults in each page's front matter (MyST
syntax shown; Sphinx RST field lists work the same way):

```markdown
---
ogp_description_length: 160
og:image: _static/og/this-page.png
og:image:alt: A tailored hero for this page
---

# Page title

Body paragraph that becomes og:description.
```

Set `ogp_disable: true` to skip OG emission on a specific page.

## Config reference

| Key | Type | Default | Purpose |
|---|---|---|---|
| `ogp_site_url` | `str` | `""` | Base URL; required for absolute `og:url` |
| `ogp_canonical_url` | `str` | `""` | Separate canonical URL; falls back to `ogp_site_url` |
| `ogp_description_length` | `int` | `200` | Description truncation cap |
| `ogp_image` | `str \| None` | `None` | Site-default OG image (1200×630 recommended) |
| `ogp_image_alt` | `str \| bool \| None` | `None` | Alt text; falls back to site name or title |
| `ogp_use_first_image` | `bool` | `False` | Use the first in-page image as `og:image` |
| `ogp_type` | `str` | `"website"` | Value of the `og:type` tag |
| `ogp_site_name` | `str \| bool \| None` | `None` (→ `project`) | `False` disables the tag |
| `ogp_custom_meta_tags` | `list[str]` | `()` | Raw `<meta>` tags emitted verbatim |
| `ogp_enable_meta_description` | `bool` | `True` | Emit a matching `<meta name="description">` |

## Differences from `sphinxext-opengraph`

Configuration is **drop-in compatible** with upstream — switching to
`gp-opengraph` does not require any conf.py changes for sites that
don't use social cards.

- **`ogp_social_cards` is accepted but ignored.** gp-opengraph does not
  bundle the matplotlib-based card generator upstream ships. Setting
  `ogp_social_cards` emits a one-line warning pointing at the static-
  image workflow below. See [Static images per page](#static-images-per-page).
- The three parser helpers (`_description`, `_title`, `_meta`) are
  ported verbatim.
- `setup()` returns `dict[str, Any]` following the gp-sphinx house
  convention; the keys (`version`, `parallel_read_safe`,
  `parallel_write_safe`) are identical.

## Static images per page

Instead of generating per-page PNGs at build time (the matplotlib
feature gp-opengraph drops), provide static images and point
frontmatter at them:

```
docs/
├── _static/
│   └── og/
│       ├── default.png     ← 1200×630, used when no frontmatter override
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

This is equivalent to upstream's auto-generated per-page cards — just
explicit.

## See also

- [gp-sitemap](https://github.com/git-pull/gp-sphinx/tree/main/packages/gp-sitemap) —
  companion package for `sitemap.xml` emission
- [gp-sphinx](https://github.com/git-pull/gp-sphinx) — the umbrella
  docs platform that auto-wires this extension from `docs_url`
