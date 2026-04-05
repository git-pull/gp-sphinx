(configuration)=

# Configuration

Reference for {py:func}`gp_sphinx.config.merge_sphinx_config` and the shared defaults
it applies.

## Integration pattern

```python
from gp_sphinx.config import merge_sphinx_config

conf = merge_sphinx_config(
    project="my-project",
    version="1.2.3",
    copyright="2026, Your Name",
    source_repository="https://github.com/your-org/my-project/",
)
globals().update(conf)
```

{py:func}`~gp_sphinx.config.merge_sphinx_config` returns a flat dictionary meant to be injected into the
module namespace with `globals().update(conf)`. That is the conventional Sphinx
integration point: Sphinx reads `conf.py` globals directly, and the returned
mapping already includes the coordinator’s generated `setup(app)` hook.

## `merge_sphinx_config()` parameters

All parameters are keyword-only.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `project` | `str` | required | Project name assigned to `project` and used in derived metadata |
| `version` | `str` | required | Version string assigned to both `version` and `release` |
| `copyright` | `str` | required | Copyright string for Sphinx metadata |
| `extensions` | `list[str] \| None` | `None` | Seed extension list; when omitted, uses `DEFAULT_EXTENSIONS` |
| `extra_extensions` | `list[str] \| None` | `None` | Additional extensions appended after the base list is chosen |
| `remove_extensions` | `list[str] \| None` | `None` | Extensions removed from the selected base list |
| `theme_options` | `dict[str, Any] \| None` | `None` | Deep-merged into `DEFAULT_THEME_OPTIONS` after auto-populated source/logo values |
| `source_repository` | `str \| None` | `None` | GitHub repository URL used for issue links, footer icon URLs, and theme source metadata |
| `source_branch` | `str` | `"main"` | Source branch stored in `html_theme_options["source_branch"]` |
| `light_logo` | `str \| None` | `None` | Light-mode logo path merged into theme options |
| `dark_logo` | `str \| None` | `None` | Dark-mode logo path merged into theme options |
| `docs_url` | `str \| None` | `None` | Canonical docs URL used to derive Open Graph settings |
| `intersphinx_mapping` | `Mapping[str, tuple[str, str \| None]] \| None` | `None` | Mapping assigned to `intersphinx_mapping` when provided |
| `**overrides` | `Any` | none | Final escape hatch for any Sphinx config key; applied after all defaults and auto-computed values |

## Auto-computed values

### From `source_repository`

| Key | Value |
| --- | --- |
| `issue_url_tpl` | `"{repo}/issues/{issue_id}"` |
| `html_theme_options["source_repository"]` | repository URL |
| `html_theme_options["footer_icons"][0]["url"]` | repository URL for the GitHub footer icon |

### From `docs_url`

| Key | Value |
| --- | --- |
| `ogp_site_url` | `docs_url` |
| `ogp_site_name` | `project` |
| `ogp_image` | `"_static/img/icons/icon-192x192.png"` |

### From `**overrides`

If `linkcode_resolve` is present in `**overrides`, `merge_sphinx_config()`
automatically appends {py:mod}`sphinx:sphinx.ext.linkcode` to `extensions` if it is not
already present.

## Injected `setup(app)`

The returned config includes a `setup(app)` function from
{py:func}`gp_sphinx.config.setup`. It does two things:

| Action | Effect |
| --- | --- |
| `app.add_js_file("js/spa-nav.js", loading_method="defer")` | Registers the bundled SPA navigation script from `sphinx-gptheme` |
| `app.connect("build-finished", remove_tabs_js)` | Removes `_static/tabs.js` after HTML builds as a `sphinx-inline-tabs` workaround |

## Always-set coordinator values

These are injected even though they are not exposed as `DEFAULT_*` constants:

| Key | Value |
| --- | --- |
| `master_doc` | `"index"` |
| `release` | `version` |
| `html_theme` | `DEFAULT_THEME` |
| `html_theme_path` | `[]` |
| `rediraffe_redirects` | `{}` |
| `rediraffe_branch` | `"master~1"` |
| `exclude_patterns` | `["_build"]` |
| `setup` | {py:func}`gp_sphinx.config.setup` |

## Shared `DEFAULT_*` constants

### Extensions and source parsing

| Constant | Value |
| --- | --- |
| `DEFAULT_EXTENSIONS` | `["sphinx.ext.autodoc", "sphinx_fonts", "sphinx.ext.intersphinx", "sphinx_autodoc_typehints", "sphinx.ext.todo", "sphinx.ext.napoleon", "sphinx_inline_tabs", "sphinx_copybutton", "sphinxext.opengraph", "sphinxext.rediraffe", "sphinx_design", "myst_parser", "linkify_issues"]` |
| `DEFAULT_SOURCE_SUFFIX` | `{".rst": "restructuredtext", ".md": "markdown"}` |
| `DEFAULT_MYST_EXTENSIONS` | `["colon_fence", "substitution", "replacements", "strikethrough", "linkify"]` |
| `DEFAULT_MYST_HEADING_ANCHORS` | `4` |
| `DEFAULT_TEMPLATES_PATH` | `["_templates"]` |
| `DEFAULT_HTML_STATIC_PATH` | `["_static"]` |

### Theme defaults

| Constant | Value |
| --- | --- |
| `DEFAULT_THEME` | `"sphinx-gptheme"` |
| `DEFAULT_THEME_OPTIONS` | footer GitHub icon, `source_repository=""`, `source_branch="main"`, `source_directory="docs/"` |

### Font defaults

| Constant | Value |
| --- | --- |
| `DEFAULT_SPHINX_FONTS` | IBM Plex Sans (400/500/600/700, normal+italic) and IBM Plex Mono (400, normal+italic) Fontsource definitions |
| `DEFAULT_SPHINX_FONT_PRELOAD` | `("IBM Plex Sans", 400, "normal")`, `("IBM Plex Sans", 700, "normal")`, `("IBM Plex Mono", 400, "normal")` |
| `DEFAULT_SPHINX_FONT_FALLBACKS` | Metric-adjusted Arial and Courier fallback declarations |
| `DEFAULT_SPHINX_FONT_CSS_VARIABLES` | `--font-stack`, `--font-stack--monospace`, `--font-stack--headings` |

### Syntax highlighting and copybutton

| Constant | Value |
| --- | --- |
| `DEFAULT_PYGMENTS_STYLE` | `"monokai"` |
| `DEFAULT_PYGMENTS_DARK_STYLE` | `"monokai"` |
| `DEFAULT_COPYBUTTON_PROMPT_TEXT` | regex matching Python, shell, and IPython prompts |
| `DEFAULT_COPYBUTTON_PROMPT_IS_REGEXP` | `True` |
| `DEFAULT_COPYBUTTON_REMOVE_PROMPTS` | `True` |
| `DEFAULT_COPYBUTTON_LINE_CONTINUATION_CHARACTER` | `"\\"` |

### Autodoc defaults

| Constant | Value |
| --- | --- |
| `DEFAULT_AUTOCLASS_CONTENT` | `"both"` |
| `DEFAULT_AUTODOC_MEMBER_ORDER` | `"bysource"` |
| `DEFAULT_AUTODOC_CLASS_SIGNATURE` | `"separated"` |
| `DEFAULT_AUTODOC_TYPEHINTS` | `"description"` |
| `DEFAULT_TOC_OBJECT_ENTRIES_SHOW_PARENTS` | `"hide"` |
| `DEFAULT_AUTODOC_OPTIONS` | `{"undoc-members": True, "members": True, "private-members": True, "show-inheritance": True, "member-order": "bysource"}` |

### Napoleon and warning defaults

| Constant | Value |
| --- | --- |
| `DEFAULT_NAPOLEON_GOOGLE_DOCSTRING` | `True` |
| `DEFAULT_NAPOLEON_INCLUDE_INIT_WITH_DOC` | `False` |
| `DEFAULT_SUPPRESS_WARNINGS` | `["sphinx_autodoc_typehints.forward_reference"]` |

## Parameter interactions

- `extensions`, `extra_extensions`, and `remove_extensions` are applied in that order.
- `theme_options` is deep-merged, so nested theme dictionaries can be overridden without replacing the whole structure.
- `**overrides` runs last, so it can replace any default or auto-computed value.
- The returned `setup(app)` hook survives `globals().update(conf)` intact because Sphinx reads it as a normal top-level `conf.py` function.
