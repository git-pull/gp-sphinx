(gp-opengraph)=

# gp-opengraph

```{gp-sphinx-package-meta} gp-opengraph
```

:::{admonition} Alpha
:class: warning

Rendered output is stable. The Python API and Sphinx config value names
may change without a major version bump. Pin your dependency to a
specific version range in production.
:::

OpenGraph and Twitter meta-tag emission for Sphinx. Drop-in replacement
for [`sphinxext-opengraph`](https://github.com/sphinx-doc/sphinxext-opengraph)
with the same `ogp_*` configuration surface, minus the matplotlib-based
social-card generator.

```console
$ pip install gp-opengraph
```

When your docs site depends on `gp-sphinx`, this extension is already
loaded in `DEFAULT_EXTENSIONS` and `ogp_site_url` / `ogp_site_name` /
`ogp_image` are auto-computed from `docs_url`. No conf.py changes
needed.

## What it emits

For every HTML-family builder page, the extension writes these `<meta>`
tags into the page head:

- `og:title` — text of the page's first heading (HTML stripped)
- `og:type` — always `"website"` (override via `ogp_type`)
- `og:url` — resolved from `ogp_site_url` + the page's relative URL
- `og:site_name` — defaults to `project`; suppressed when
  `ogp_site_name = False`
- `og:description` — first body paragraph, truncated to
  `ogp_description_length` (default 200 chars)
- `og:image` and `og:image:alt` — when `ogp_image` is set or the page
  carries an `og:image` frontmatter override
- `<meta name="description">` — auto-emitted to match `og:description`
  unless the page already defines one or
  `ogp_enable_meta_description = False`

Plus any raw tags listed in `ogp_custom_meta_tags` (emit Twitter cards,
`og:image:width`/`og:image:height` dimension hints, etc. here).

## Migration from `sphinxext-opengraph`

`conf.py` files using the upstream extension keep working — every
`ogp_*` key is registered with identical semantics, **except**:

- `ogp_social_cards` is accepted but **ignored**. gp-opengraph does not
  bundle the matplotlib-based card generator. Setting this config key
  emits a one-line warning pointing at the static-image workflow.

For per-page social card images, use static PNGs and point frontmatter
at them:

```markdown
---
og:image: _static/og/my-page.png
---

# My page
```

## Package reference

```{package-reference} gp-opengraph
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/gp-opengraph) · [PyPI](https://pypi.org/project/gp-opengraph/)
