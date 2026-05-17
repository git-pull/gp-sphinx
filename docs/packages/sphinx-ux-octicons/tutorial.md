(sphinx-ux-octicons-tutorial)=

# Tutorial

## Add the extension

`sphinx-ux-octicons` is loaded automatically by
{py:func}`~gp_sphinx.config.merge_sphinx_config`. To use it in a
standalone Sphinx project, list it in `conf.py`:

```python
extensions = ["sphinx_ux_octicons"]
```

## Use the role

The `{octicon}` role accepts an icon name and emits an inline SVG.

```markdown
Welcome {octicon}`rocket`!
```

Welcome {octicon}`rocket`!

## Size an icon

Pass a CSS length as the second argument, separated by `;`.

```markdown
{octicon}`book;1.5rem` Documentation
```

{octicon}`book;1.5rem` Documentation

## Add extra classes

Pass a space-separated list of class names as the third argument.

```markdown
{octicon}`alert;1em;text-warning` heads up
```

{octicon}`alert;1em;text-warning` heads up

The rendered SVG inherits its colour from `currentColor`, so wrapping
the role in a coloured container (a heading, an admonition, a span
with a colour utility) tints the icon without per-role styling.
