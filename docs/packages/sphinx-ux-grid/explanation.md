(sphinx-ux-grid-explanation)=

# Explanation

## CSS Grid, not Bootstrap floats

Older grid systems (Bootstrap 4 and earlier) built columns out of
`float: left` with negative margins. `sphinx-ux-grid` uses CSS Grid
directly: every grid is `display: grid` with
`grid-template-columns: repeat(N, minmax(0, 1fr))`. The breakpoint
column count is set per-grid via inline custom properties, and the
static CSS reads the property at each media query.

The upshot:

- Items size proportionally without `width: percentage` arithmetic.
- Gutter is a single `gap` declaration, not nested padding.
- A single rule set in the CSS file handles every grid invocation,
  regardless of how many appear on a page.

## Plain `nodes.container`, not custom nodes

The directives emit
{py:class}`docutils.nodes.container` with class names. There is no
custom node subclass for the grid itself.

This is deliberate. The grid is presentation-only — every behaviour
worth describing (column count, gutter, alignment, links) is encoded
in a CSS class or an inline custom property. Non-HTML builders
(LaTeX, text, man) descend into the container's children and render
the content; the layout disappears without breaking the doctree.

The exception is the card's link target. To preserve a Sphinx
cross-reference resolution path for `:link-type: doc` and `:ref`, the
directive emits a thin `LinkPassthrough(nodes.TextElement)` that
hosts an `addnodes.pending_xref` or `nodes.reference`. This sidesteps
Sphinx's `HTML5Translator.visit_reference` assertion that a reference
node containing more than one child must wrap a single image — a
constraint that prevents wrapping the entire card container in a
reference.

## Breakpoint values as inline custom properties

The straightforward way to make a grid responsive is to write one CSS
rule per (grid × breakpoint) combination — but that produces an
unbounded number of selectors as the docs grow. Instead, the
directive emits one `style="..."` declaration per grid:

```html
<div class="gp-sphinx-grid"
     style="--gp-sphinx-grid-cols-xs: 1; --gp-sphinx-grid-cols-sm: 2;
            --gp-sphinx-grid-cols-md: 3; --gp-sphinx-grid-cols-lg: 4;
            --gp-sphinx-grid-gutter: 1rem">
```

The static CSS file has a finite set of rules consuming these
properties via `var()`:

```css
.gp-sphinx-grid {
  grid-template-columns: repeat(var(--gp-sphinx-grid-cols-xs, 1), minmax(0, 1fr));
}
@media (min-width: 576px) {
  .gp-sphinx-grid {
    grid-template-columns: repeat(var(--gp-sphinx-grid-cols-sm, 1), minmax(0, 1fr));
  }
}
```

This pattern is repeated for margin and padding. The rendered CSS
stays a constant size; per-grid variation lives entirely in inline
styles.

## Comparison to sphinx-design

`sphinx-design` ships a much larger surface: dropdowns, plain cards,
buttons, article-info, Material and FontAwesome icons,
card-carousels, tab-set-code. `sphinx-ux-grid` is intentionally
narrow — just the grid and card directives gp-sphinx actually uses.

The MyST authoring surface is unchanged: `{grid}`, `{grid-item}`,
`{grid-item-card}`, and their option names, all match sphinx-design.
Source written against sphinx-design's grid works against this
package without edits.

## Comparison to Furo's `sd-card`

Furo's bundled CSS includes overrides for sphinx-design's
`.sd-card`/`.sd-row` classes. This package uses its own
`gp-sphinx-grid*` namespace under `@layer gp-sphinx`, which sits
between Furo's `components` and `utilities` layers. Project-level
overrides win because they target the package's namespaced classes
directly.
