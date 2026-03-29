# sphinx-fonts

Sphinx extension for self-hosted fonts via [Fontsource](https://fontsource.org/) CDN.

Downloads font files at build time, caches them locally (`~/.cache/sphinx-fonts`), and
injects `@font-face` declarations via Jinja2 template context.

## Install

```console
$ pip install sphinx-fonts
```

## Usage

In your `docs/conf.py`:

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

sphinx_font_css_variables = {
    "--font-stack": '"IBM Plex Sans", sans-serif',
}
```

Requires a `page.html` template override that reads the `font_faces` and
`font_preload_hrefs` context variables. See the
[gp-sphinx docs](https://gp-sphinx.git-pull.com) for a complete template example.
