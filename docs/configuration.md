(configuration)=

# Configuration

Reference for `merge_sphinx_config()` and the shared defaults it applies.

## merge_sphinx_config()

All parameters are keyword-only.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project` | `str` | required | Sphinx project name |
| `version` | `str` | required | Project version (also sets `release`) |
| `copyright` | `str` | required | Copyright string |
| `extensions` | `list[str] \| None` | `None` | Replace entire extension list (overrides defaults) |
| `extra_extensions` | `list[str] \| None` | `None` | Append to default extension list |
| `remove_extensions` | `list[str] \| None` | `None` | Remove specific extensions from defaults |
| `theme_options` | `dict \| None` | `None` | Deep-merged with `DEFAULT_THEME_OPTIONS` |
| `source_repository` | `str \| None` | `None` | GitHub URL (auto-computes `issue_url_tpl` and footer icon) |
| `source_branch` | `str` | `"master"` | Default branch name |
| `light_logo` / `dark_logo` | `str \| None` | `None` | Theme logo paths |
| `docs_url` | `str \| None` | `None` | Docs URL (auto-computes OGP settings) |
| `intersphinx_mapping` | `Mapping \| None` | `None` | Intersphinx targets |
| `**overrides` | `Any` | — | Any Sphinx config key, passed through verbatim |

`**overrides` is the escape hatch — any valid Sphinx configuration key can be
passed as a keyword argument. This includes extension-specific settings like
`rediraffe_redirects`, `pytest_fixture_lint_level`, or `html_favicon`.
Auto-computed values can also be overridden this way.

## Auto-computed values

When `source_repository` is provided:

- `issue_url_tpl` for `linkify_issues`
- `html_theme_options["source_repository"]`
- Footer icon GitHub URL

When `docs_url` is provided:

- `ogp_site_url` for `sphinxext.opengraph`
- `ogp_site_name` (set to project name)
- `ogp_image` (`_static/img/icons/icon-192x192.png`)

When `linkcode_resolve` is in `**overrides`:

- `sphinx.ext.linkcode` is auto-appended to extensions

## Hardcoded defaults

Set unconditionally. Override via `**overrides` if needed:

| Key | Value |
|-----|-------|
| `master_doc` | `"index"` |
| `release` | same as `version` |
| `source_suffix` | `{".rst": "restructuredtext", ".md": "markdown"}` |
| `html_static_path` | `["_static"]` |
| `templates_path` | `["_templates"]` |
| `pygments_style` | `"monokai"` |
| `pygments_dark_style` | `"monokai"` |
| `exclude_patterns` | `["_build"]` |

## Injected setup()

The returned config includes a `setup` function that:

- Registers `js/spa-nav.js` with deferred loading (from sphinx-gptheme)
- Connects a `build-finished` hook to remove `tabs.js` (sphinx-inline-tabs workaround)

## Integration pattern

```python
conf = merge_sphinx_config(...)
globals().update(conf)
```

This injects all keys into the module namespace, which is how Sphinx
reads `conf.py`.

## Default extensions

| Extension | Purpose |
|-----------|---------|
| `sphinx.ext.autodoc` | Auto-document Python objects |
| `sphinx_fonts` | Self-hosted fonts via Fontsource CDN |
| `sphinx.ext.intersphinx` | Cross-project linking |
| `sphinx_autodoc_typehints` | Type hints in docstrings |
| `sphinx.ext.todo` | TODO directive |
| `sphinx.ext.napoleon` | NumPy/Google docstring support |
| `sphinx_inline_tabs` | Inline tab containers |
| `sphinx_copybutton` | Copy button on code blocks |
| `sphinxext.opengraph` | OpenGraph meta tags |
| `sphinxext.rediraffe` | URL redirects |
| `sphinx_design` | Cards, grids, badges |
| `myst_parser` | Markdown support |
| `linkify_issues` | Auto-link `#123` to issues (from gp-libs) |

## Default theme

`sphinx-gptheme` — Furo child theme. Source directory `docs/`, source
branch `master`, GitHub footer icon. Theme options are deep-merged when
`theme_options` is passed.

## Font defaults

- **IBM Plex Sans**: weights 400, 500, 600, 700 (normal + italic)
- **IBM Plex Mono**: weight 400 (normal + italic)
- **Preload**: Sans 400 normal, Sans 700 normal, Mono 400 normal
- **Fallbacks**: metric-matched Arial/Courier New for zero-CLS loading
- **CSS variables**: `--font-stack`, `--font-stack--monospace`, `--font-stack--headings`

## MyST defaults

Extensions: `colon_fence`, `substitution`, `replacements`, `strikethrough`, `linkify`.
Heading anchors: 4 levels.

## Autodoc defaults

`DEFAULT_AUTODOC_OPTIONS`:

| Setting | Value |
|---------|-------|
| `autoclass_content` | `"both"` |
| `autodoc_member_order` | `"bysource"` |
| `autodoc_class_signature` | `"separated"` |
| `autodoc_typehints` | `"description"` |
| `toc_object_entries_show_parents` | `"hide"` |

`DEFAULT_AUTODOC_OPTIONS` dict (applied to `autodoc_default_options`):

| Key | Value |
|-----|-------|
| `members` | `True` |
| `undoc-members` | `True` |
| `private-members` | `False` |
| `show-inheritance` | `True` |
| `member-order` | `"bysource"` |

## Static paths and source suffix

| Constant | Value |
|----------|-------|
| `DEFAULT_SOURCE_SUFFIX` | `{".rst": "restructuredtext", ".md": "markdown"}` |
| `DEFAULT_HTML_STATIC_PATH` | `["_static"]` |
| `DEFAULT_TEMPLATES_PATH` | `["_templates"]` |

## Copybutton defaults

`DEFAULT_COPYBUTTON_PROMPT_TEXT` — regex matching Python (`>>>`), continuation (`...`), shell (`$`, `#`), and IPython prompts. See `defaults.py` for the full pattern.

| Constant | Value |
|----------|-------|
| `DEFAULT_COPYBUTTON_PROMPT_IS_REGEXP` | `True` |
| `DEFAULT_COPYBUTTON_REMOVE_PROMPTS` | `True` |
| `DEFAULT_COPYBUTTON_LINE_CONTINUATION_CHARACTER` | `"\\"` |

## Other defaults

| Constant | Value |
|----------|-------|
| `DEFAULT_NAPOLEON_GOOGLE_DOCSTRING` | `True` |
| `DEFAULT_NAPOLEON_INCLUDE_INIT_WITH_DOC` | `False` |
| `DEFAULT_SUPPRESS_WARNINGS` | `["sphinx_autodoc_typehints.forward_reference"]` |

Rediraffe: `rediraffe_redirects = {}`, `rediraffe_branch = "master~1"`.
