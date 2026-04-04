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

| Config value | Type | Default (via gp-sphinx) | Description |
|-------------|------|------------------------|-------------|
| `sphinx_fonts` | `list[dict]` | IBM Plex Sans (400/500/600/700, normal+italic), IBM Plex Mono (400, normal+italic) | Font family definitions |
| `sphinx_font_preload` | `list[tuple]` | Sans 400 normal, Sans 700 normal, Mono 400 normal | Critical variants to preload |
| `sphinx_font_fallbacks` | `list[dict]` | Metric-matched Arial/Courier New with size_adjust | Fallback font faces for CLS reduction |
| `sphinx_font_css_variables` | `dict` | `--font-stack`, `--font-stack--monospace`, `--font-stack--headings` | CSS custom properties for Furo font stacks |

Each font dict in `sphinx_fonts` has the shape:

```python
{
    "family": "IBM Plex Sans",
    "package": "@fontsource/ibm-plex-sans",
    "version": "5.2.8",
    "weights": [400, 500, 600, 700],
    "styles": ["normal", "italic"],
}
```

## How it works

1. **`builder-inited`**: Downloads font files from Fontsource CDN, caches in `~/.cache/sphinx-fonts`, copies to `_static/fonts/`
2. **`html-page-context`**: Injects structured data into the Jinja2 template context

### Template context variables

The extension makes these variables available to theme templates:

| Variable | Type | Description |
|----------|------|-------------|
| `font_faces` | `list[dict]` | `@font-face` declaration data (family, src, weight, style, unicode-range) |
| `font_preload_hrefs` | `list[str]` | `<link rel="preload">` href values for critical fonts |
| `font_fallbacks` | `list[dict]` | Fallback `@font-face` declarations with metric overrides |
| `font_css_variables` | `dict[str, str]` | CSS custom properties for font stacks |

Theme templates consume these to generate inline CSS. When using
sphinx-gptheme, this is handled automatically.

This site uses IBM Plex Sans and Mono via sphinx-fonts.

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/master/packages/sphinx-fonts)
