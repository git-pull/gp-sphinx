# gp-furo-theme

A Tailwind-v4-driven port of the [Furo](https://github.com/pradyunsg/furo)
Sphinx theme for git-pull project documentation. Renders byte-equivalent HTML
and visually-equivalent CSS to upstream Furo while sourcing all styles from
Tailwind v4 layers and the `@gp-sphinx/furo-tokens` package.

## Status

Skeleton — only the theme registration hook (`setup()`) is wired up. Template
ports, asset pipeline, and Python hooks (`_html_page_context`,
`_builder_inited`, `_overwrite_pygments_css`, `_asset_hash`,
`WrapTableAndMathInAContainerTransform`) land in subsequent commits.

## Usage (eventual)

```python
# conf.py
html_theme = "gp-furo"
```

## Attribution

Templates, styles, and scripts are ported from upstream Furo at the commit
pinned in `../gp-furo-tokens/upstream/furo-vars.json`. Furo is MIT-licensed
by Pradyun Gedam; the full license text is reproduced at `LICENSE-FURO`.
Each ported file carries a 3-line attribution header pointing at upstream.
