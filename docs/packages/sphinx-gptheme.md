# sphinx-gptheme

{bdg-success-line}`Beta`

Furo child theme for git-pull documentation sites. It keeps Furo’s responsive
layout and dark mode, then layers in shared sidebars, typography, source-link
controls, metadata toggles, and SPA-style navigation.

```console
$ pip install sphinx-gptheme
```

## Downstream `conf.py`

```python
extensions = ["sphinx_gptheme"]
html_theme = "sphinx-gptheme"

html_theme_options = {
    "project_name": "my-project",
    "project_description": "Shared docs for my project.",
    "light_logo": "img/logo-light.svg",
    "dark_logo": "img/logo-dark.svg",
    "source_repository": "https://github.com/your-org/my-project/",
    "source_branch": "main",
    "source_directory": "docs/",
}
```

## Live theme notes

- This site is rendered with `sphinx-gptheme`.
- The package badges, cards, sidebar project list, and deferred page transitions on this page are live theme output.
- Dark mode is inherited from Furo; the theme options below control the extra git-pull behavior layered on top.

## Theme options

Options declared in `theme.conf` and accepted through `html_theme_options`:

| Option | Description |
| --- | --- |
| `announcement` | Banner content rendered above the header |
| `dark_css_variables` | Dark-mode CSS variable overrides |
| `dark_logo` | Logo path for dark mode |
| `footer_icons` | Footer icon list with `name`, `url`, `html`, and `class` keys |
| `light_css_variables` | Light-mode CSS variable overrides |
| `light_logo` | Logo path for light mode |
| `mask_icon` | Safari pinned-tab icon |
| `project_description` | Project summary used by sidebar/meta templates |
| `project_name` | Short project name |
| `project_title` | Alternate long-form title |
| `project_url` | Canonical project home URL |
| `show_meta_app_icon_tags` | Emit app icon meta tags |
| `show_meta_manifest_tag` | Emit web manifest link tag |
| `show_meta_og_tags` | Emit Open Graph tags |
| `sidebar_hide_name` | Hide the sidebar brand name when a logo is present |
| `source_branch` | Source branch used for edit/view links |
| `source_directory` | Repository path containing docs sources |
| `source_edit_link` | Override the generated edit link |
| `source_repository` | Repository URL used for source links and footer GitHub icon |
| `source_view_link` | Override the generated view-source link |
| `top_of_page_button` | Single top-of-page action, defaults to `edit` |
| `top_of_page_buttons` | Multiple top-of-page actions |

## Bundled assets

| File | Purpose |
| --- | --- |
| `theme/sidebar/brand.html` | Sidebar brand block |
| `theme/sidebar/projects.html` | Cross-project navigation |
| `theme/static/css/custom.css` | Base layout and typography overrides |
| `theme/static/css/argparse-highlight.css` | CLI lexer highlighting rules |
| `theme/static/js/spa-nav.js` | Deferred navigation enhancer |

## Relationship to gp-sphinx

`gp-sphinx` sets this theme automatically via `merge_sphinx_config()` and
pre-populates `source_repository`, `source_branch`, `source_directory`, footer
icons, and the IBM Plex font stacks consumed by the theme templates.

```{package-reference} sphinx-gptheme
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gptheme)
