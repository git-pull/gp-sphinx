# gp-furo-theme

```{gp-sphinx-package-meta} gp-furo-theme
```

Tailwind-v4-driven port of the [Furo](https://github.com/pradyunsg/furo)
Sphinx theme. Renders byte-equivalent HTML and visually-equivalent CSS to
upstream Furo while owning every template, style, and script — no `furo`
dependency. Lands alongside `sphinx-gp-theme` during the soft transition
described in `whats-new`; will become the workspace default once
byte-equivalence tests cover the full gp-sphinx docs surface.

```console
$ pip install gp-furo-theme
```

## Status

Skeleton — only theme registration is wired. Template ports, asset pipeline,
and Python hooks (`_html_page_context`, `_builder_inited`,
`_overwrite_pygments_css`, `_asset_hash`,
`WrapTableAndMathInAContainerTransform`) land in subsequent commits.

## Downstream `conf.py` (eventual)

```python
extensions = ["gp_furo_theme"]
html_theme = "gp-furo"
```

## Attribution

Templates, styles, and scripts are ported from upstream Furo at the commit
pinned in `packages/gp-furo-tokens/upstream/furo-vars.json`. Furo is
MIT-licensed by Pradyun Gedam; the full license text is reproduced at
`packages/gp-furo-theme/LICENSE-FURO`. Each ported file carries a 3-line
attribution header pointing at upstream.

```{package-reference} gp-furo-theme
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/gp-furo-theme)
