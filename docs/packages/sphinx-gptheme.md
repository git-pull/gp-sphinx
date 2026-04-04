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

## What it provides

- **Templates**: `page.html`, `sidebar/brand.html`, `sidebar/projects.html`
- **Static assets**: `css/custom.css`, `js/spa-nav.js`
- **Parent theme**: Furo (declared in `theme.conf` with `inherit = furo`)
- **Entry point**: registered via `sphinx.html_themes` as `"sphinx-gptheme"`

## SPA navigation

`spa-nav.js` intercepts internal link clicks and swaps page content without
a full page reload, preserving scroll position and sidebar state. Loaded
with `defer` by the `setup()` function injected by `merge_sphinx_config()`.

This site is built with sphinx-gptheme.

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/master/packages/sphinx-gptheme)
