(sphinx-ux-grid-reference)=

# API Reference

## Directives

### `{grid}`

Container for grid items. Lays out children in a CSS-Grid template
whose column count varies by breakpoint.

```{list-table}
:header-rows: 1
:widths: 20 20 60

* - Option
  - Value
  - Description
* - argument
  - `<int>` or `<int> <int> <int> <int>`
  - Column counts. Single integer applies to every breakpoint; four
    integers map to `xs sm md lg` (defaults: 1, 1, 2, 2).
* - `:gutter:`
  - `0`–`5` or four such values
  - Spacing scale. `0` → `0`, `1` → `0.25rem`, ..., `5` → `3rem`.
    Defaults to `3`.
* - `:margin:`
  - `0`–`5`, `auto`, or four such values
  - Margin scale, per breakpoint.
* - `:padding:`
  - `0`–`5` or four such values
  - Padding scale, per breakpoint.
* - `:outline:`
  - flag
  - Render a faint outline around the grid container (debugging
    helper).
* - `:reverse:`
  - flag
  - Reverse the visual order of grid items without changing source
    order.
* - `:class-container:`
  - string
  - Append classes to the grid container.
* - `:class-row:`
  - string
  - Append classes to the inner row wrapper.
```

### `{grid-item}`

Child of `{grid}`. Carries column-span overrides for itself.

```{list-table}
:header-rows: 1
:widths: 20 20 60

* - Option
  - Value
  - Description
* - `:columns:`
  - `<int>` or four ints (1..12)
  - Column span, per breakpoint. Default inherits the parent grid's
    breakpoint columns.
* - `:child-direction:`
  - `column` or `row`
  - Direction the item's children flow.
* - `:child-align:`
  - `start`, `end`, `center`, `justify`, `spaced`
  - Alignment of the item's children.
* - `:margin:`
  - `0`–`5`, `auto`, or four such values
  - Margin scale, per breakpoint.
* - `:padding:`
  - `0`–`5` or four such values
  - Padding scale, per breakpoint.
* - `:outline:`
  - flag
  - Debug outline.
* - `:class:`
  - string
  - Append classes to the item.
```

### `{grid-item-card}`

Composite: a `{grid-item}` wrapping a card. Accepts every `{grid-item}`
option plus card-specific options below.

```{list-table}
:header-rows: 1
:widths: 20 20 60

* - Option
  - Value
  - Description
* - argument
  - inline text
  - Card title.
* - `:link:`
  - target string
  - Make the card clickable. Combined with `:link-type:`.
* - `:link-type:`
  - `url`, `any`, `ref`, `doc`
  - How `:link:` is resolved. Default `any` (tries `doc` then `ref`).
* - `:link-alt:`
  - string
  - Accessible label for the link.
* - `:shadow:`
  - `none`, `sm`, `md`, `lg`
  - Card shadow strength.
* - `:width:`
  - `25%`, `50%`, `75%`, `100%`, `auto`
  - Card width override.
* - `:text-align:`
  - `left`, `center`, `right`, `justify`
  - Body text alignment.
* - `:img-top:`
  - image path
  - Image rendered above the body.
* - `:img-bottom:`
  - image path
  - Image rendered below the body.
* - `:img-background:`
  - image path
  - Image rendered behind the body.
* - `:img-alt:`
  - string
  - Alt text for the image.
* - `:class-item:`
  - string
  - Classes appended to the outer grid-item wrapper.
* - `:class-card:`
  - string
  - Classes appended to the card container.
* - `:class-body:`
  - string
  - Classes appended to the card body.
* - `:class-title:`
  - string
  - Classes appended to the card title.
* - `:class-header:`
  - string
  - Classes appended to the card header.
* - `:class-footer:`
  - string
  - Classes appended to the card footer.
```

#### Card content splitters

Inside a `{grid-item-card}`, two markers split the body:

- `^^^` — separator between header and body.
- `+++` — separator between body and footer.

The header, body, and footer each receive their own
`.gp-sphinx-grid-card__header` / `__body` / `__footer` container.

## CSS classes

```{list-table}
:header-rows: 1
:widths: 35 65

* - Class
  - Applied to
* - `gp-sphinx-grid`
  - The grid container.
* - `gp-sphinx-grid__item`
  - Each grid item wrapper.
* - `gp-sphinx-grid-card`
  - The card element inside `{grid-item-card}`.
* - `gp-sphinx-grid-card__body`
  - Card body region.
* - `gp-sphinx-grid-card__title`
  - Card title.
* - `gp-sphinx-grid-card__header`
  - Header region (above `^^^`).
* - `gp-sphinx-grid-card__footer`
  - Footer region (below `+++`).
* - `gp-sphinx-grid-card__img-top`
  - Top-positioned image.
* - `gp-sphinx-grid-card__img-bottom`
  - Bottom-positioned image.
* - `gp-sphinx-grid-card__link`
  - Stretched-link anchor that makes the whole card clickable.
* - `gp-sphinx-grid-card--shadow-sm`
  - Modifier — small shadow.
* - `gp-sphinx-grid-card--shadow-md`
  - Modifier — medium shadow.
* - `gp-sphinx-grid-card--shadow-lg`
  - Modifier — large shadow.
* - `gp-sphinx-grid-card--outline`
  - Modifier — render with an outline instead of a shadow.
* - `gp-sphinx-grid--reverse`
  - Modifier — reverse visual order.
```

## CSS custom properties

The grid container reads breakpoint values from inline custom
properties; the package's CSS file declares the rules that consume
them. Override defaults via your project's `custom.css`.

```{list-table}
:header-rows: 1
:widths: 40 60

* - Property
  - Purpose
* - `--gp-sphinx-grid-cols-xs`
  - Column count at extra-small width.
* - `--gp-sphinx-grid-cols-sm`
  - Column count at small width (≥ 576px).
* - `--gp-sphinx-grid-cols-md`
  - Column count at medium width (≥ 768px).
* - `--gp-sphinx-grid-cols-lg`
  - Column count at large width (≥ 992px).
* - `--gp-sphinx-grid-gutter`
  - Gap between grid items.
* - `--gp-sphinx-grid-margin-{xs,sm,md,lg}`
  - Margin per breakpoint.
* - `--gp-sphinx-grid-padding-{xs,sm,md,lg}`
  - Padding per breakpoint.
```

The directive emits these as inline `style="..."` overrides on the
grid container. The static CSS rules consume them with the
established cascade (each breakpoint's rule reads the matching
property and falls back to the previous breakpoint).

## Python API

```{eval-rst}
.. autofunction:: sphinx_ux_grid.setup
```
