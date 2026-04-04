# sphinx-gptheme

{bdg-success-line}`Beta` {bdg-info}`theme`

Furo child theme for [git-pull](https://github.com/git-pull) project
documentation. Inherits Furo's responsive layout and dark mode, adding a
custom sidebar with project links, footer icons, SPA-style page navigation,
and CSS variable-driven IBM Plex typography.

```console
$ pip install sphinx-gptheme
```

## Usage

```python
html_theme = "sphinx-gptheme"
```

When used with gp-sphinx, the theme is set automatically by
`merge_sphinx_config()`.

## Theme options

Options declared in `theme.conf` (passed via `html_theme_options`):

| Option | Description |
|--------|-------------|
| `announcement` | Banner text displayed above the header |
| `light_logo` | Logo path for light mode |
| `dark_logo` | Logo path for dark mode |
| `sidebar_hide_name` | Hide project name in sidebar brand |
| `footer_icons` | List of footer icon dicts (`name`, `url`, `html`, `class`) |
| `light_css_variables` | CSS custom property overrides for light mode |
| `dark_css_variables` | CSS custom property overrides for dark mode |

### Example

```python
html_theme_options = {
    "light_logo": "img/my-logo.svg",
    "dark_logo": "img/my-logo-dark.svg",
    "announcement": "<em>Note:</em> This project is in alpha.",
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/my-org/my-project",
            "html": "<svg>...</svg>",
            "class": "",
        },
    ],
}
```

## Bundled assets

### Templates

| Template | Description |
|----------|-------------|
| `sidebar/brand.html` | Project logo and name |
| `sidebar/projects.html` | Cross-project navigation links |

### Stylesheets

| File | Description |
|------|-------------|
| `css/custom.css` | Base typography and layout overrides |
| `css/argparse-highlight.css` | Syntax colors for CLI output lexers |

### JavaScript

| File | Description |
|------|-------------|
| `js/spa-nav.js` | SPA-style page navigation (deferred loading) |

## Inheritance

- **Parent theme**: Furo (`inherit = furo` in `theme.conf`)
- **Entry point**: registered via `sphinx.html_themes` as `"sphinx-gptheme"`
- **Sidebars**: scroll-start, brand, search, navigation, projects, scroll-end

This site is built with sphinx-gptheme.

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/master/packages/sphinx-gptheme)
