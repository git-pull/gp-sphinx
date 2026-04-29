(sphinx-gp-opengraph)=

# sphinx-gp-opengraph

```{gp-sphinx-package-meta} sphinx-gp-opengraph
```

:::{admonition} Alpha
:class: warning

Rendered output is stable. The Python API and Sphinx config value names
may change without a major version bump. Pin your dependency to a
specific version range in production.
:::

OpenGraph meta-tag emission for Sphinx. The package registers every
`ogp_*` config value the upstream
[`sphinxext-opengraph`](https://github.com/sphinx-doc/sphinxext-opengraph)
exposes and emits the same `<meta>` tags, with one deliberate
omission: the matplotlib-based social-card generator is not bundled.
That is why the package has zero non-Sphinx runtime dependencies.

For install, per-page overrides, Twitter-card markup, and the
verbatim deprecation-warning text, see the package
[README](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-opengraph#readme).
This page covers integration with gp-sphinx, the emission pipeline,
the trade-offs, and the auto-generated config-value reference.

## Integration with gp-sphinx

`sphinx_gp_opengraph` ships in {py:data}`~gp_sphinx.defaults.DEFAULT_EXTENSIONS`,
so projects that build through {py:func}`~gp_sphinx.config.merge_sphinx_config`
load it automatically. Passing `docs_url=` to that function auto-derives
three of the most common config values:

| Auto-derived | Source |
| --- | --- |
| `ogp_site_url` | `docs_url` |
| `ogp_site_name` | `project` |
| `ogp_image` | `"_static/img/icons/icon-192x192.png"` |

The canonical reference for these and the other auto-derived values
lives in {ref}`from-docs_url`. Any value passed via `**overrides` to
`merge_sphinx_config()` wins over the auto-derived default —
auto-computation runs first, overrides apply last.

## How the page-level meta tags are built

For every page rendered by an HTML-family builder, the extension's
`html-page-context` handler walks the resolved doctree and emits the
following tags into `context["metatags"]`. The page is skipped when its
front-matter sets `ogp_disable: true`.

| Tag | Source |
| --- | --- |
| `og:title` | First heading of the page, with HTML stripped (`_title.py`) |
| `og:type` | `ogp_type` (default `"website"`) |
| `og:url` | `ogp_canonical_url or ogp_site_url`, joined with the page's relative URL |
| `og:site_name` | `ogp_site_name`, or `project` when unset; suppressed when set to `False` |
| `og:description` | First non-title body paragraph, truncated to `ogp_description_length`, HTML-escaped (`_description.py`) |
| `og:image` | Page front-matter `og:image`, else `ogp_image`, else first in-page image when `ogp_use_first_image=True` |
| `og:image:alt` | Front-matter `og:image:alt`, else `ogp_image_alt`, falling back to site name, then page title |
| `<meta name="description">` | Mirror of `og:description` when `ogp_enable_meta_description=True` and the page does not already define one (`_meta.py`) |

The description extractor walks the document, skips title nodes and
empty paragraphs, takes the first prose paragraph, and truncates at the
configured cap. Embedded HTML quote characters are escaped with
`&quot;` before emission, so user content cannot break out of the
attribute value.

Custom raw markup listed in `ogp_custom_meta_tags` is appended verbatim
after the structured tags — that is the supported escape hatch for
Twitter card declarations and `og:image:width`/`og:image:height` hints.

## Event hooks

```text
config-inited     →  _warn_if_social_cards_used     (deprecation warning)
html-page-context →  html_page_context              (per-page meta-tag emission)
```

Both hooks live in
[`sphinx_gp_opengraph/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-opengraph/src/sphinx_gp_opengraph/__init__.py).
There is no `builder-inited` or `build-finished` work — the extension
is purely a per-page transformer.

## Trade-offs

**`ogp_social_cards` is accepted but ignored.** The upstream extension
ships a matplotlib renderer that builds per-page PNGs at
`builder-inited`. sphinx-gp-opengraph deliberately omits the dependency to
keep the install graph small. The config key remains registered so
existing `conf.py` files do not error; setting it logs a single
`WARNING` at `config-inited` directing users to the static-image
workflow documented in the README.

**`parallel_read_safe` and `parallel_write_safe` are both `True`.**
The extension never writes shared state — every emission is
self-contained inside the per-page hook — so it is safe under any
`sphinx-build -j N` value.

## Config reference

Generated from `app.add_config_value()` registrations in
[`sphinx_gp_opengraph/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-opengraph/src/sphinx_gp_opengraph/__init__.py).

```{eval-rst}
.. autoconfigvalues:: sphinx_gp_opengraph
```

## Package reference

```{package-reference} sphinx-gp-opengraph
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-opengraph) · [PyPI](https://pypi.org/project/sphinx-gp-opengraph/)
