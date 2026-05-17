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

## CSS classes

```{list-table}
:header-rows: 1
:widths: 35 65

* - Class
  - Applied to
* - `gp-sphinx-tabs`
  - Outer tab-set container.
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

## Python API

```{eval-rst}
.. autofunction:: sphinx_ux_tabs.setup
```
