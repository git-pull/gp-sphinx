(sphinx-ux-grid-examples)=

# Examples

## Four-breakpoint responsive grid

Resize the browser to see the column count change.

::::{grid} 1 2 3 4
:gutter: 3

:::{grid-item-card} {octicon}`rocket` Tutorial
:link: tutorial
:link-type: doc
Working usage examples for `{grid}` and `{grid-item-card}`.
:::

:::{grid-item-card} {octicon}`tools` How to
:link: how-to
:link-type: doc
Recipes for sync groups, links, images, and overrides.
:::

:::{grid-item-card} {octicon}`book` Reference
:link: reference
:link-type: doc
Option reference for every directive.
:::

:::{grid-item-card} {octicon}`light-bulb` Explanation
:link: explanation
:link-type: doc
Why CSS Grid, why custom properties, why one node.
:::
::::

## Cards with header / body / footer

Markers `^^^` and `+++` split the card body into three regions.

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} Three regions
{bdg-primary}`Header`
^^^
Body text describing the card's main content. Renders inside
`.gp-sphinx-grid-card__body`.
+++
{octicon}`info` Footer with a different background tint.
:::

:::{grid-item-card} Two regions (body + footer)
Body-only opening — no `^^^` marker, so the card has no header.
+++
{bdg-success}`Stable` · {bdg-info-line}`v0.0.1`
:::
::::

## Mixed-span items inside one grid

`{grid-item}` accepts its own `:columns:` to override the parent
grid's breakpoint defaults.

::::{grid} 1 2 4 4
:gutter: 3

:::{grid-item}
:columns: 4 4 4 4
:class: gp-sphinx-grid-card gp-sphinx-grid-card--outline
Full-width across mobile, then quarter-width on tablet and desktop.
:::

:::{grid-item-card}
Standard card.
:::

:::{grid-item-card}
Standard card.
:::

:::{grid-item-card}
Standard card.
:::
::::

## Outline cards (no shadow)

::::{grid} 1 2 2 2
:gutter: 2

:::{grid-item-card} Subtle framing
:outline:
Low-density framing without a drop shadow. Useful for content
indexes.
:::

:::{grid-item-card} {octicon}`star` Highlight
:outline:
Compose with `{octicon}` for an icon next to the title.
:::
::::

## RST authoring

The directives also work in reStructuredText. The rendered HTML is
identical to the MyST forms above.

```{eval-rst}
.. grid:: 1 2 3 3
   :gutter: 3

   .. grid-item-card:: First
      :shadow: sm

      Authored in reStructuredText.

   .. grid-item-card:: Second
      :shadow: sm

      Same ``gp-sphinx-grid-card`` HTML as MyST source.

   .. grid-item-card:: Third
      :shadow: sm

      Mix RST and MyST in the same project — both authoring
      surfaces produce the same DOM.
```
