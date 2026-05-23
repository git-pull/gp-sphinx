(sphinx-ux-grid-how-to)=

# How to

## Mix columns within a grid

`{grid-item}` accepts its own `:columns:` argument that overrides the
parent grid's breakpoint defaults for that one item:

````markdown
:::{grid} 1 2 3 4

:::{grid-item}
:columns: 12 12 12 12
Full-width hero spanning every breakpoint.
:::

:::{grid-item-card}
Normal-width sibling.
:::

:::
````

`:columns:` takes the same single-int or four-int values as the
parent's column count.

## Compose with icons and badges

Cards compose with [`sphinx-ux-octicons`](../sphinx-ux-octicons/index.md)
and [`sphinx-ux-badges`](../sphinx-ux-badges/index.md):

````markdown
:::{grid-item-card} {octicon}`rocket` Quickstart
:link: quickstart
:link-type: doc
{bdg-success}`Stable`
^^^
Install and get started in minutes.
:::
````

## Outline cards

Use `:outline:` to swap the shadow for a border. Common for cards in
documentation indexes where you want low-density framing:

```markdown
:::{grid-item-card} Reference
:outline:
:link: reference
:link-type: doc
API reference for every directive and option.
:::
```

## Image-only cards

`:img-background:` puts an image behind the card body. `:img-top:` /
`:img-bottom:` places an image above or below the body:

```markdown
:::{grid-item-card} Gallery
:img-top: _static/gallery-hero.png
:img-alt: A wide shot of the gallery
A walkthrough of every component.
:::
```

## Reverse a grid's visual order

`:reverse:` flips the grid items' visual order without changing
source order. Useful when you want the most recent item to appear
first visually but you author it last:

```markdown
:::{grid} 1 1 2 2
:reverse:
:gutter: 3

:::{grid-item-card} Older item
:::
:::{grid-item-card} Newer item
:::

:::
```

## Apply custom margins via the spacing scale

The `:margin:` and `:padding:` options accept the integer scale
`0..5` or the keyword `auto`. Each integer maps to a CSS length
(`0` → `0`, `1` → `0.25rem`, ..., `5` → `3rem`). Pass one value to
apply to every breakpoint, or four values for `xs sm md lg`:

```markdown
:::{grid} 1 2 3 4
:gutter: 3
:margin: 0 0 4 4

Spacious only on tablet and desktop.
:::
```

## Override classes from MyST source

Every card section accepts a class override via the relevant
`:class-*:` option (`:class-container:`, `:class-row:`,
`:class-item:`, `:class-card:`, `:class-body:`, `:class-title:`,
`:class-header:`, `:class-footer:`):

```markdown
:::{grid-item-card} Custom card
:class-card: my-project-callout
Body text.
:::
```

The class names are appended to the rendered element. The package's
own `gp-sphinx-grid*` classes are always present.
