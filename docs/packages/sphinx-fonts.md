# sphinx-fonts

{bdg-success-line}`Beta` {bdg-primary}`extension`

Sphinx extension for self-hosted web fonts via Fontsource. It downloads font
assets during the HTML build, caches them locally, copies them into
`_static/fonts/`, and exposes template context values that themes can render as
inline `@font-face` and preload tags.

```console
$ pip install sphinx-fonts
```

## Downstream `conf.py`

```python
extensions = ["sphinx_fonts"]

sphinx_fonts = [
    {
        "family": "IBM Plex Sans",
        "package": "@fontsource/ibm-plex-sans",
        "version": "5.2.8",
        "weights": [400, 500, 600, 700],
        "styles": ["normal", "italic"],
        "subset": "latin",
    },
]

sphinx_font_preload = [
    ("IBM Plex Sans", 400, "normal"),
]

sphinx_font_css_variables = {
    "--font-stack": '"IBM Plex Sans", system-ui, sans-serif',
}
```

## Live specimen

This site uses `sphinx-fonts`, so the samples below are rendered with the same
template context that downstream themes receive.

```{raw} html
<div class="package-demo-grid">
  <div class="package-demo-card">
    <h3>Sans stack</h3>
    <p class="font-specimen-sans">Sphinx DX should feel intentional, readable, and fast.</p>
  </div>
  <div class="package-demo-card">
    <h3>Monospace stack</h3>
    <p class="font-specimen-mono">merge_sphinx_config(project="demo", version="1.0.0")</p>
  </div>
</div>
```

## Configuration values

```{eval-rst}
.. autoconfigvalue-index:: sphinx_fonts
.. autoconfigvalues:: sphinx_fonts
```

## Template context

The extension injects these values during `html-page-context`:

| Variable | Type | Description |
| --- | --- | --- |
| `font_faces` | `list[dict[str, str]]` | File metadata for generated `@font-face` declarations |
| `font_preload_hrefs` | `list[str]` | Font filenames to preload |
| `font_fallbacks` | `list[dict[str, str]]` | Metric-adjusted fallback declarations |
| `font_css_variables` | `dict[str, str]` | CSS custom properties for theme font stacks |

## Notes

- Fonts are cached under `~/.cache/sphinx-fonts`.
- Non-HTML builders return early and do not download assets.
- `sphinx-gptheme` consumes this template context automatically; `gp-sphinx` preconfigures IBM Plex defaults for it.

```{package-reference} sphinx-fonts
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/master/packages/sphinx-fonts)
