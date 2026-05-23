(sphinx-ux-tabs-explanation)=

# Explanation

## Radio inputs and CSS-only switching

Tabs are rendered as a group of `<input type="radio">` elements
sharing a `name` attribute, each followed by a `<label for="...">`
and a content panel `<div>`. CSS handles which panel is visible:

```css
.gp-sphinx-tabs__input:checked + .gp-sphinx-tabs__label + .gp-sphinx-tabs__panel {
  display: block;
}
```

The labels are visually styled buttons; the inputs are visually
hidden via `position: absolute; clip: rect(0 0 0 0)` but remain
focusable for keyboard navigation. Browser-native radio semantics
handle arrow-key navigation between labels.

The upshot: tabs work without JavaScript. JS is needed only for
cross-tab-set synchronization.

## Two authoring surfaces, one rendered output

`sphinx-inline-tabs` and `sphinx-design` shipped different authoring
syntaxes for the same concept:

- `.. tab::` — flat siblings, consecutive runs auto-group.
- `.. tab-set::` + `.. tab-item::` — explicit container with named
  children.

The flat style reads well in long-form prose where each tab is
shorter than a paragraph. The nested style reads well when each tab
contains multiple paragraphs or when explicit grouping aids
readability. Source written against either upstream works against
this package unchanged.

The rendered HTML structure is identical regardless of authoring
style. Both produce a single `gp-sphinx-tabs` container with the same
radio/label/panel triples per tab.

## Two-pass post-transform

A single Sphinx post-transform handles both authoring styles:

1. **Group consecutive `.. tab::` siblings** into a synthesized
   `TabSetNode`. The `:new-set:` flag forces a stack break.
   Non-tab content between siblings also breaks the run. Nested
   `.. tab::` inside another tab's content forms a nested tab-set.
2. **Expand every `TabSetNode`** (whether from the grouping pass or
   from a `{tab-set}` directive) into the radio-input HTML structure.
   The first explicit `:selected:` wins, falling back to index 0 if
   none is set; multiple `:selected:` emit a warning.

Both passes run only for HTML builds (`formats = ("html",)`). Other
builders see plain containers and `TextElement` labels, which render
cleanly without the radio plumbing.

## SPA-safe sync

The workspace's SPA navigation replaces the entire
`.article-container` on each navigation, dispatching a
`gp-sphinx:navigated` event after the swap. The tab-sync JS:

1. Re-runs its binding function on every navigation event.
2. Uses an idempotent `data-gp-sphinx-tabs-bound` marker on each
   label, so labels carried over from a previous page aren't bound
   twice.
3. Re-queries the whole document on each navigation rather than
   relying on a scoped root — the only labels that match the
   `:not([data-gp-sphinx-tabs-bound])` selector are the freshly
   inserted ones.

The pattern fixes a class of bug that broke `sphinx-inline-tabs`'
upstream sync JS in SPA-navigated documentation sites: its `tabs.js`
ran once on `DOMContentLoaded`, never re-bound after navigation, and
silently stopped working when the user clicked a link.

## Comparison to sphinx-inline-tabs and sphinx-design

The authoring surfaces of both upstream packages are preserved
exactly:

- `.. tab::` and `:new-set:` from sphinx-inline-tabs.
- `.. tab-set::`, `.. tab-item::`, `:selected:`, `:sync:`, `:name:`,
  `:sync-group:` from sphinx-design.

The rendered HTML uses the `gp-sphinx-tabs__*` BEM namespace instead
of either upstream's classes. The sync JS is SPA-aware and idempotent.
And the package ships ~50 lines of static CSS instead of either
upstream's larger compiled bundles.

CSS-only switching means consumers can disable the sync JS entirely
(remove the `add_js_file` line in `setup()`) and tabs continue to
work — they just don't synchronize across tab-sets on the page.
