(sphinx-ux-octicons-how-to)=

# How to

## Icon in a heading

Inline `{octicon}` works anywhere a role is allowed, including
headings:

```markdown
## {octicon}`book` Reference
```

The icon inherits the heading's colour and scales with the heading's
font size when the role's height argument is `1em` (the default).

## Icon inside a grid card title

`{octicon}` composes with [`sphinx-ux-grid`](../sphinx-ux-grid/index.md)
to put an icon next to a card title:

```markdown
:::{grid-item-card} {octicon}`rocket` Quickstart
:link: quickstart
:link-type: doc
Install and get started in minutes.
:::
```

## Match the rendered SVG to a colour

`gp-sphinx-octicon` uses `fill: currentColor`. Override the colour by
wrapping the role in a span carrying a colour class, or by setting
`color` on the parent element via your project's `custom.css`:

```css
.my-warning {
  color: var(--color-attention-foreground, #b08800);
}
```

```markdown
<span class="my-warning">{octicon}`alert` Heads up</span>
```

## Add a new icon to the bundle

The bundle is hand-curated to keep the wheel small. Add a name to
`_data/octicons_curated.txt` and regenerate `_data/octicons.json` from
upstream `@primer/octicons`:

```console
$ cd packages/sphinx-ux-octicons
$ pnpm install @primer/octicons
$ python scripts/sync_octicons.py node_modules/@primer/octicons/build/svg
```

Commit both files together so the JSON and the audit-source-of-truth
text file stay in sync.
