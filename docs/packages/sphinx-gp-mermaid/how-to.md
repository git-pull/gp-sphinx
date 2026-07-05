(sphinx-gp-mermaid-how-to)=

# How to

## Author a diagram

Write a diagram in a MyST fence — it renders to inline SVG at build time, so it paints with the page and needs no client-side script:

```markdown
:::{mermaid}
:caption: How a request flows.
:alt: browser request through the CDN to the origin
:name: request-flow
:responsive: fit

flowchart LR
    browser --> cdn --> origin
:::
```

`:caption:`, `:alt:`, `:name:`, `:class:`, and `:responsive:` are the directive's options; `:name:` gives the figure a cross-reference target. When you build through {py:func}`~gp_sphinx.config.merge_sphinx_config` with the extension in `extra_extensions`, plain {rst:dir}`mermaid` fences route to the same directive automatically (it sets `myst_fence_as_directive = ["mermaid"]`).

See {ref}`sphinx-gp-mermaid-reference` for the full option and config list.

## Choose the responsive policy

Every rendered diagram sits in a scrollable figure. The `:responsive:` option decides what the SVG itself does inside that figure:

- `fit` is the default. It keeps the SVG's build-time aspect ratio but lets the browser scale the diagram down to the content column.
- `preserve` keeps the SVG at its intrinsic Mermaid-rendered width. If the diagram is wider than the column, the figure scrolls horizontally.

Use `fit` for diagrams that remain readable when scaled: small flows, state diagrams, and short sequence diagrams. Use `preserve` for diagrams where scale-down would make labels unreadable, such as dense architecture maps or compatibility matrices.

```markdown
:::{mermaid}
:caption: Dense architecture map.
:alt: subsystem ownership and data flow
:name: architecture-map
:responsive: preserve

flowchart LR
    api --> planner --> executor --> sinks
    planner --> cache
    executor --> audit
:::
```

`fit` and `preserve` do not rewrite the Mermaid graph. If a wide `flowchart LR` turns into a hard-to-read strip on phones, split it into smaller diagrams or use a top-to-bottom layout. Reach for `preserve` when the wide view is the useful artifact.

## Install the renderer

Rendering shells out to [`mmdc`](https://github.com/mermaid-js/mermaid-cli), so the docs toolchain needs Node. Install it as a dev dependency:

```console
$ pnpm add -D @mermaid-js/mermaid-cli
```

The extension finds `mmdc` from the {confval}`mermaid_cmd` config value, then `<confdir>/node_modules/.bin/mmdc`, then `PATH`. `mmdc` drives a headless Chrome through puppeteer — build-time rendering costs a Node and Chrome toolchain in CI, which consumers of your published docs never pay.

In a container, set `PUPPETEER_EXECUTABLE_PATH` to your Chrome (the generated puppeteer config keeps the `--no-sandbox` args), or point {confval}`mermaid_puppeteer_config` at your own config file.

## How rendering behaves

Each diagram renders twice — a light and a dark SVG — and CSS on `body[data-theme]` shows the matching one, so the theme toggle works with no JavaScript and no layout shift. The HTML figure carries `gp-sphinx-mermaid--fit` or `gp-sphinx-mermaid--preserve`, plus `data-mermaid-responsive`, `data-mermaid-width`, and `data-mermaid-height` attributes for downstream styling or audits. Rendered SVGs are cached by content hash under `<confdir>/_mermaid_cache`, which lives outside `_build` and survives `rm -rf docs/_build`, so a clean rebuild re-renders nothing unchanged.

If `mmdc` is missing or fails, the build still succeeds: the diagram degrades to its escaped source text with a single warning, and non-HTML builders emit a `[diagram: <alt>]` stand-in.
