# sphinx-ux-grid

CSS-Grid-backed `{grid}`, `{grid-item}`, and `{grid-item-card}` directives
under the `gp-sphinx-grid` CSS namespace.

The directives are a drop-in alternative to sphinx-design's grid markup:
they accept the same option names (`:gutter:`, `:columns:`, `:link:`,
`:link-type:`, `:shadow:`, `:img-top:`, …) and the same `^^^`/`+++`
header/footer split inside `{grid-item-card}`. The layout is plain CSS
Grid; per-directive overrides flow through CSS custom properties inlined
on each container's `style` attribute, so no Bootstrap-derived float
classes are emitted and degradation to text/man/latex falls out of the
underlying `nodes.container` writer.

## Install

```console
$ pip install sphinx-ux-grid
```

## Usage

Add the extension to your `conf.py`:

```python
extensions = ["sphinx_ux_grid"]
```

Then write a grid in MyST or reStructuredText:

```markdown
::::{grid} 1 2 3 4
:gutter: 3

:::{grid-item-card} First
:link: page-one
:link-type: doc

Card body content.

+++

Card footer.
:::

:::{grid-item-card} Second
:link: https://example.com
:link-type: url

Body only.
:::
::::
```
