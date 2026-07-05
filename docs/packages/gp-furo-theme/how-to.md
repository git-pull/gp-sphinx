(gp-furo-theme-how-to)=

# How to

Use `gp-furo-theme` when you want the git-pull Tailwind port of [Furo]
directly, outside the coordinator defaults that {doc}`/packages/gp-sphinx/index`
supplies.

## Downstream `conf.py`

```python
extensions = ["gp_furo_theme"]
html_theme = "gp-furo"
```

## CSS authoring layout

The asset pipeline lives in `packages/gp-furo-theme/web/`:

```
web/
├── package.json              # tailwindcss, @tailwindcss/vite, typescript
├── vite.config.ts            # two rollup entries: scripts/furo, styles/furo-tw
└── src/
    ├── scripts/
    │   ├── furo.ts           # strict-typed port of upstream furo.js
    │   └── gumshoe.js        # vendored; UMD→ESM surgery only
    └── styles/
        ├── index.css         # entry: @import "tailwindcss" + @plugin
        │                     #        + @custom-variant dark
        │                     #        + per-component imports
        └── components/
            ├── base.css            # typography, links, .visually-hidden, print
            ├── typography.css      # article-class typography + :target
            ├── lists.css           # ul/ol/dl + .field-list / .option-list
            ├── tables.css, footnotes.css, captions.css,
            ├── images.css, math.css, blocks.css
            ├── admonitions.css     # 11 type variants + mask-image icons
            ├── code.css            # inline + block + linenos + copybutton
            ├── api.css             # autodoc signatures + version banners
            ├── search.css          # results listing
            ├── scaffold.css        # 3-col layout + responsive drawers
            ├── sidebar.css         # toctree-checkbox toggle + brand
            ├── toc.css             # scroll-spy active state
            ├── footer.css          # bottom-of-page + related-pages
            └── extensions.css      # sphinx-design / inline-tabs / copybutton
```

The 153 Furo CSS custom properties (light + dark) come from
`@gp-sphinx/furo-tokens`'s Tailwind v4 plugin; component CSS references
them via `var(--color-foreground-primary)` etc. so dark-mode swaps work
at runtime via `body[data-theme="dark"]`.

## Visual fidelity

Verified by `tests/visual/test_visual_regression.py`: 12 representative
pages × 2 modes × 3 viewports = 72 baseline screenshots captured from
the previously vendored SCSS pipeline. The current Tailwind output
diffs at ~20% average against those baselines — driven mostly by minor
margin/padding deltas that propagate through long scrolling pages.
Per-page tightening to <0.5% is iterative follow-up work.

Behavioral parity is verified by `tests/visual/test_furo_behaviors.py`
(mobile sidebar drawer, skip-to-content focus; theme-toggle / scroll-spy
/ back-to-top documented and skipped pending a switch to mouse-wheel-
synthesised scroll events — see test docstrings).

## Attribution

Templates, scripts, and Python hooks are ported from upstream Furo at
commit `b788b8a41aea7323b541975590a284f9f9db8f8e`. Furo is MIT-licensed
by Pradyun Gedam; the full license text is reproduced at
`packages/gp-furo-theme/LICENSE-FURO`. Each ported file carries a
1-line attribution header pointing at upstream. The CSS files
(re-authored in pure Tailwind v4 from upstream's SCSS, file-by-file)
carry the same attribution pointing at the upstream SCSS source they
replicate.

```{package-reference} gp-furo-theme
```

[Furo]: https://github.com/pradyunsg/furo
[Vite]: https://vitejs.dev
