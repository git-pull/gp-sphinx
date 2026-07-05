(sphinx-gp-mermaid-how-to)=

# How to

## Author a diagram

Write a diagram in a MyST fence — it renders to inline SVG at build time, so it paints with the page and needs no client-side script:

```markdown
:::{mermaid}
:caption: How a request flows.

flowchart LR
    browser --> cdn --> origin
:::
```

`:caption:`, `:alt:`, and `:name:` are the directive's options; `:name:` gives the figure a cross-reference target. When you build through {py:func}`~gp_sphinx.config.merge_sphinx_config` with the extension in `extra_extensions`, plain {rst:dir}`mermaid` fences route to the same directive automatically (it sets `myst_fence_as_directive = ["mermaid"]`).

See {ref}`sphinx-gp-mermaid-reference` for the full option and config list.

## Install the renderer

Rendering shells out to [`mmdc`](https://github.com/mermaid-js/mermaid-cli), so the docs toolchain needs Node. Install it as a dev dependency:

```console
$ pnpm add -D @mermaid-js/mermaid-cli
```

The extension finds `mmdc` from the `mermaid_cmd` config value, then `<confdir>/node_modules/.bin/mmdc`, then `PATH`. `mmdc` drives a headless Chrome through puppeteer — build-time rendering costs a Node and Chrome toolchain in CI, which consumers of your published docs never pay.

In a container, set `PUPPETEER_EXECUTABLE_PATH` to your Chrome (the generated puppeteer config keeps the `--no-sandbox` args), or point `mermaid_puppeteer_config` at your own config file.

## How rendering behaves

Each diagram renders twice — a light and a dark SVG — and CSS on `body[data-theme]` shows the matching one, so the theme toggle works with no JavaScript and no layout shift. Rendered SVGs are cached by content hash under `<confdir>/_mermaid_cache`, which lives outside `_build` and survives `rm -rf docs/_build`, so a clean rebuild re-renders nothing unchanged.

If `mmdc` is missing or fails, the build still succeeds: the diagram degrades to its escaped source text with a single warning, and non-HTML builders emit a `[diagram: <alt>]` stand-in.
