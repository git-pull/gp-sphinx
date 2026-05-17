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

## Use tabs after SPA navigation

Tabs work without JS — the `:checked + label + .panel` selectors
handle switching. The sync JS listens for the workspace's
`gp-sphinx:navigated` event and re-binds click handlers on
freshly-swapped labels. The idempotent `data-gp-sphinx-tabs-bound`
marker ensures each label is bound exactly once.

No special author action is required — sync works on every page,
including pages loaded via SPA navigation.
