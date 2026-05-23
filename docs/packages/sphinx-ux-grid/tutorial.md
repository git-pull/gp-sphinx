(sphinx-ux-grid-tutorial)=

# Tutorial

## Add the extension

`sphinx-ux-grid` is loaded automatically by
{py:func}`~gp_sphinx.config.merge_sphinx_config`. To use it in a
standalone Sphinx project:

```python
extensions = ["sphinx_ux_grid"]
```

## A responsive grid

The `{grid}` directive accepts a breakpoint argument of either a
single integer or four space-separated integers (`xs sm md lg`):

````markdown
:::{grid} 1 2 3 4
:gutter: 3

:::{grid-item-card} Quickstart
Install and get started in minutes.
:::

:::{grid-item-card} Reference
Full API documentation.
:::

:::{grid-item-card} Examples
Live demos.
:::

:::{grid-item-card} Source
GitHub source for every package.
:::

:::
````

The grid renders 1 column on phones, 2 on small tablets, 3 on
tablets, and 4 on desktops.

## A card with a link

Cards become clickable when `:link:` is set. `:link-type:` controls
how the link is resolved:

- `url` — bare HTML link
- `doc` — Sphinx docname (e.g. `packages/sphinx-ux-tabs/index`)
- `ref` — `:ref:` label
- `any` — try `doc` first, then `ref` (the default)

```markdown
:::{grid-item-card} Quickstart
:link: quickstart
:link-type: doc
:shadow: md
Install and get started in minutes.
:::
```

The whole card is clickable. The internal `.gp-sphinx-grid-card__link`
covers the card via `position: absolute; inset: 0`.

## Header and footer markers

Inside `{grid-item-card}`, two markers split the card body into
sections:

- `^^^` — everything above is the header.
- `+++` — everything below is the footer.

````markdown
:::{grid-item-card} Card with sections
header text
^^^
body text
+++
footer text
:::
````
