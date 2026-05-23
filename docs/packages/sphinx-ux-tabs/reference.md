(sphinx-ux-tabs-reference)=

# API Reference

## Directives

### `.. tab::` (sphinx-inline-tabs style)

Single tab. Consecutive `.. tab::` siblings group into one tab-set
during a post-transform.

```{list-table}
:header-rows: 1
:widths: 20 20 60

* - Option
  - Value
  - Description
* - argument
  - inline text
  - Tab label (required).
* - `:new-set:`
  - flag
  - Force a fresh tab-set break, even if the previous sibling is also
    a `.. tab::`.
* - `:selected:`
  - flag
  - Pre-check this tab. First-wins if multiple carry `:selected:`.
```

### `{tab-set}` (sphinx-design style)

Explicit container for `{tab-item}` children.

```{list-table}
:header-rows: 1
:widths: 20 20 60

* - Option
  - Value
  - Description
* - `:sync-group:`
  - string
  - Group key for cross-page tab synchronization. Default `"tab"`.
* - `:class:`
  - string
  - Append classes to the rendered container.
```

### `{tab-item}` (sphinx-design style)

A single tab inside a `{tab-set}`. Must be a direct child.

```{list-table}
:header-rows: 1
:widths: 20 20 60

* - Option
  - Value
  - Description
* - argument
  - inline text
  - Tab label (required).
* - `:selected:`
  - flag
  - Pre-check this tab.
* - `:sync:`
  - string
  - Sync key. All `tab-item`s with the same `:sync:` value in the
    same `:sync-group:` follow each other when the user clicks.
* - `:name:`
  - string
  - Cross-reference target registered on the tab's label.
* - `:class-container:`
  - string
  - Classes appended to the tab's panel container.
* - `:class-label:`
  - string
  - Classes appended to the tab's label.
* - `:class-content:`
  - string
  - Classes appended to the tab's content container.
```

## Doctree nodes

`sphinx-ux-tabs` registers five custom nodes. Visitors are registered
for `html`; non-HTML builders fall back via MRO to the parent class
(`nodes.container` or `nodes.TextElement`).

```{list-table}
:header-rows: 1
:widths: 25 30 45

* - Node
  - Parent
  - Purpose
* - `TabContainer`
  - `nodes.container`
  - Transient — emitted by `.. tab::`, consumed by the post-transform
    grouping pass.
* - `TabSetNode`
  - `nodes.container`
  - Final tab-set after grouping/expansion. Carries `tabset_id`.
* - `TabItemNode`
  - `nodes.container`
  - Final tab item with `sync_id`, `sync_group`, `selected` attrs.
* - `TabInputNode`
  - `nodes.Element`
  - Void HTML `<input type="radio">` element.
* - `TabLabelNode`
  - `nodes.TextElement`
  - `<label for="...">` element. Carries cross-reference `ids` /
    `names`.
```

## Post-transform

`TabsPostTransform` runs at priority 200 against HTML formats only.
Two passes:

1. **Group pass** — collects consecutive `TabContainer` siblings into
   a synthesized `TabSetNode`. `:new-set:` forces a stack break.
   Non-tab content between siblings also breaks the run.
2. **Expansion pass** — for every `TabSetNode`, assigns a
   document-wide unique `tabset_id` and replaces each `TabItemNode`
   with a `[TabInputNode, TabLabelNode, panel-container]` triple.

The first tab with `:selected:` wins. If none is selected, index 0 is
checked. Multiple `:selected:` tabs emit a Sphinx warning under the
subtype `gp-sphinx-tabs.tab`.

## Size variants

The default size renders labels at `0.95em` with tight padding to match
the workspace's compact prose rhythm. Authors can opt into a larger
size with `:class: gp-sphinx-tabs--large` on `{tab-set}` — labels paint
at normal body size with roomier padding, suitable for callout
sections, feature-comparison tables, or landing-page hero tabs.

````markdown
:::{tab-set}
:class: gp-sphinx-tabs--large

:::{tab-item} pip
`pip install gp-sphinx`
:::

:::{tab-item} uv
`uv add gp-sphinx`
:::

:::
````

The `:class:` option preserves BEM `--` modifiers verbatim.
`sphinx-ux-tabs` uses a custom class-option parser specifically so the
`gp-sphinx-tabs--large` token survives — docutils' built-in
`class_option` would collapse the `--` to a single `-`.

## Persistence and deep-links

`sphinx-ux-tabs` persists each user's tab choice and accepts URL query
parameters to deep-link a specific tab.

### localStorage

Every `:sync-group:` gets its own `localStorage` key under the
namespace `gp-sphinx-tabs.sync.<group>`. On click, the JS writes the
chosen `:sync:` ID under that key. On script-load and on every
`gp-sphinx:navigated` event (workspace SPA navigation), the JS reads
every distinct `data-sync-group` on the page and restores the saved
selection.

### URL query parameters

URL query parameters take precedence over `localStorage` on first
paint and write through to `localStorage` so the choice persists for
subsequent visits. Two formats are accepted:

```{list-table}
:header-rows: 1
:widths: 30 70

* - Form
  - Behaviour
* - `?tabs=Label`
  - sphinx-inline-tabs idiom — matches by tab label text,
    case-insensitive. Pre-selects every label whose visible text equals
    `Label`.
* - `?<group>=<id>`
  - sphinx-design idiom — matches by `:sync-group:` / `:sync:`.
    Multiple `?key=val` pairs accumulate, one per distinct group.
```

URL parameters apply on first paint only. Subsequent SPA-nav events
read from `localStorage` only — re-applying URL params on every
navigation would let stale query strings override a fresh click.

## CSS classes

```{list-table}
:header-rows: 1
:widths: 35 65

* - Class
  - Applied to
* - `gp-sphinx-tabs`
  - Outer tab-set container.
* - `gp-sphinx-tabs--large`
  - Modifier on `gp-sphinx-tabs` opting into the larger size variant.
* - `gp-sphinx-tabs__input`
  - Hidden radio input (`<input type="radio">`).
* - `gp-sphinx-tabs__label`
  - Clickable tab label (`<label for="...">`).
* - `gp-sphinx-tabs__panel`
  - Tab content panel.
```

## CSS custom properties

```{list-table}
:header-rows: 1
:widths: 40 60

* - Property
  - Purpose
* - `--gp-sphinx-tabs-active-fg`
  - Foreground colour of the active tab label.
* - `--gp-sphinx-tabs-active-border`
  - Border colour of the active tab label.
* - `--gp-sphinx-tabs-inactive-fg`
  - Foreground colour of inactive tab labels.
```

Defaults chain to Furo's `--color-brand-primary`,
`--color-foreground-muted`, `--color-background-border` so the tabs
inherit theme switching automatically.

## JavaScript

The shipped sync JS is page-scoped, idempotent, and SPA-aware:

```{list-table}
:header-rows: 1
:widths: 30 70

* - Hook
  - Behaviour
* - Script-load
  - Binds click handlers on every `[data-sync-id]` label that isn't
    yet marked with `data-gp-sphinx-tabs-bound`.
* - `gp-sphinx:navigated`
  - Re-binds handlers on freshly-swapped labels after SPA navigation.
* - Click on a sync label
  - Re-checks every matching radio (same `data-sync-id` AND
    `data-sync-group`) across the document.
```

Tabs work without the JS — pure CSS handles single-page switching.
The JS is only needed for cross-tab-set sync.

### Prehydrate

Pages that host sync'd tabs receive a small inline `<head>` payload —
a `<script data-cfasync="false">` and a `<style>` block under
`@layer gp-sphinx-tabs-prehydrate`. The script reads URL query
parameters and `localStorage`, then sets
`<html data-gp-sphinx-tabs-sync-<group>="<id>">` before any stylesheet
loads. The CSS layer's attribute selectors then paint the saved
label colour and panel visibility on the first frame, so the user
never sees the server-rendered default tab flash to the saved
selection.

`data-cfasync="false"` opts the inline script out of Cloudflare Rocket
Loader so it runs synchronously as written. Pages without sync'd tabs
carry zero prehydrate payload — the prehydrate injection short-circuits
when the post-transform records no `(sync_group, sync_id)` pairs for
the page.

## Python API

```{eval-rst}
.. autofunction:: sphinx_ux_tabs.setup
```
