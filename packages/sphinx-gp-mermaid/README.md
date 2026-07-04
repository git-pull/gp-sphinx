# sphinx-gp-mermaid

Build-time Mermaid diagrams for Sphinx. Fenced `mermaid` blocks render to
inline `<svg>` during the build via `mmdc`
([@mermaid-js/mermaid-cli](https://github.com/mermaid-js/mermaid-cli)):
no client-side mermaid runtime, no asynchronous pop-in, no layout shift.

Each diagram is rendered twice — a light and a dark variant — and both are
inlined, toggled by CSS on `body[data-theme]`. Diagrams paint with the page,
follow the theme toggle without JavaScript, and survive SPA navigation as
live DOM.

## Install

```console
$ pip install sphinx-gp-mermaid
```

## Usage

Enable the extension in `conf.py`:

```python
extensions = ["sphinx_gp_mermaid"]
```

With gp-sphinx, opt in via `merge_sphinx_config`:

```python
config = merge_sphinx_config(
    extra_extensions=["sphinx_gp_mermaid"],
)
```

Author diagrams as MyST fences:

````markdown
:::{mermaid}
:caption: How it flows.

flowchart LR
    a --> b
:::
````

## Renderer toolchain

Rendering shells out to `mmdc`, resolved from the `mermaid_cmd` config value,
then `<confdir>/node_modules/.bin/mmdc`, then `PATH`. Install it in the docs
toolchain:

```console
$ pnpm add -D @mermaid-js/mermaid-cli
```

When the renderer is unavailable the build still succeeds: diagrams degrade
to their source text with a single warning.

## Documentation

See the [full documentation](https://gp-sphinx.git-pull.com/packages/sphinx-gp-mermaid/)
for directive options, theming, caching, and CI setup.
