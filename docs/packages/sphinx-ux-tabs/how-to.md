(sphinx-ux-tabs-how-to)=

# How to

## Select a non-first tab by default

Set `:selected:` on the `tab-item` that should be active when the page
loads:

````markdown
:::{tab-set}

:::{tab-item} Linux
Steps for Linux.
:::

:::{tab-item} macOS
:selected:
Steps for macOS — selected by default.
:::

:::{tab-item} Windows
Steps for Windows.
:::

:::
````

If multiple tabs carry `:selected:`, the first wins and Sphinx emits
a build-time warning.

## Synchronize tabs across the page

`:sync:` lets the user pick a value once and have every related
tab-set follow. Tabs that share a `:sync:` key sync as a group; the
default group is `"tab"`, override with `:sync-group:` on the
containing `{tab-set}` for an isolated group.

````markdown
::::{tab-set}
:sync-group: shell

:::{tab-item} bash
:sync: bash
Steps for bash.
:::

:::{tab-item} zsh
:sync: zsh
Steps for zsh.
:::
::::

Later on the page:

::::{tab-set}
:sync-group: shell

:::{tab-item} bash
:sync: bash
More bash steps — sync follows the user's earlier selection.
:::

:::{tab-item} zsh
:sync: zsh
More zsh steps.
:::
::::
````

The bundled JS at `_static/js/sphinx_ux_tabs_sync.js` watches label
clicks and re-checks every matching radio across the document.

## Cross-reference a tab

`:name:` registers a cross-reference target on the tab's label. Use
`{ref}` with the registered name and an explicit visible text:

```markdown
:::{tab-set}

:::{tab-item} Python
:name: py-tab
Python content.
:::

:::

Later: see {ref}`the Python tab <py-tab>` for details.
```

The label is the anchor — clicking the `{ref}` jumps to the tab's
label, the radio remains in whichever state the user last selected.

## Deep-link to a specific tab

`sphinx-ux-tabs` reads two URL query-parameter forms on first paint and
writes the resolved selection through to `localStorage`, so a link
that sets a tab also persists the choice for the user's next visit.

The label form deep-links by visible text — appropriate when the link
target shouldn't care about authoring details:

```
https://example.org/install/?tabs=Python
```

The group form deep-links by the `:sync-group:` / `:sync:` pair —
appropriate when more than one tab on the page shares a label, or when
the link should target a specific sync-group:

```
https://example.org/install/?shell=zsh
```

Both forms persist to `localStorage` under the key
`gp-sphinx-tabs.sync.<group>`, so the next page load on the same
sync-group restores the user's last choice automatically. URL params
apply on first paint only — subsequent SPA-nav events read from
`localStorage`.

## Use the larger size variant

The default tab size is compact (`0.95em` labels) to match the
workspace's tight prose rhythm. Use `:class: gp-sphinx-tabs--large` on
the `{tab-set}` for callout sections, feature-comparison tables, or
landing-page hero tabs — anywhere touch-target size or label
prominence matters more than vertical economy.

````markdown
:::{tab-set}
:class: gp-sphinx-tabs--large

:::{tab-item} pip
...
:::

:::{tab-item} uv
...
:::

:::
````

The `:class:` option preserves the BEM `--` modifier verbatim — no
extra escaping required.

## Use tabs after SPA navigation

Tabs work without JS — the `:checked + label + .panel` selectors
handle switching. The sync JS listens for the workspace's
`gp-sphinx:navigated` event and re-binds click handlers on
freshly-swapped labels. The idempotent `data-gp-sphinx-tabs-bound`
marker ensures each label is bound exactly once.

No special author action is required — sync works on every page,
including pages loaded via SPA navigation.
