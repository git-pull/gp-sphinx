# sphinx-fonts

{bdg-success-line}`Beta` {bdg-primary}`extension`

Self-hosted web fonts via [Fontsource](https://fontsource.org/) CDN. Downloads
font files at build time, caches them locally, and injects structured font data
into the template context for inline `@font-face` CSS generation.

```console
$ pip install sphinx-fonts
```

## Usage

In `conf.py`:

```python
extensions = ["sphinx_fonts"]

sphinx_fonts = [
    {
        "family": "IBM Plex Sans",
        "package": "@fontsource/ibm-plex-sans",
        "version": "5.2.8",
        "weights": [400, 500, 600, 700],
        "styles": ["normal", "italic"],
    },
]
```

When used with gp-sphinx, font configuration is provided by default — IBM Plex
Sans and IBM Plex Mono are pre-configured with preload hints and fallback
font-metric overrides for zero-CLS loading.

## Configuration

| Config value | Type | Description |
|-------------|------|-------------|
| `sphinx_fonts` | `list[dict]` | Font family definitions (family, package, version, weights, styles) |
| `sphinx_font_preload` | `list[tuple]` | Critical variants to preload (family, weight, style) |
| `sphinx_font_fallbacks` | `list[dict]` | Metric-matched fallback font faces |
| `sphinx_font_css_variables` | `dict` | CSS custom properties for Furo font stacks |

## How it works

1. **`builder-inited`**: Downloads font files from Fontsource CDN, caches in `~/.cache/sphinx-fonts`
2. **`html-page-context`**: Injects font face data, preload `<link>` hrefs, fallbacks, and CSS variables into the Jinja2 template context

This site uses IBM Plex Sans and Mono via sphinx-fonts.

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/master/packages/sphinx-fonts)
