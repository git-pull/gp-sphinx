(sphinx-ux-tabs-tutorial)=

# Tutorial

## Add the extension

`sphinx-ux-tabs` is loaded automatically by
{py:func}`~gp_sphinx.config.merge_sphinx_config`. To use it in a
standalone Sphinx project:

```python
extensions = ["sphinx_ux_tabs"]
```

## Inline-tabs style (RST)

Consecutive `.. tab::` directives group automatically into a single
tab-set. The first tab is selected by default.

```rst
.. tab:: Python

   ``hello world`` in Python.

.. tab:: Rust

   ``hello world`` in Rust.

.. tab:: Go

   ``hello world`` in Go.
```

The author writes each `.. tab::` independently; the post-transform
collapses consecutive siblings into one tab-set during the HTML build.

## Tab-set style (MyST)

Use `{tab-set}` and `{tab-item}` when you want an explicit container,
or when you need MyST-only syntax.

````markdown
:::{tab-set}

:::{tab-item} Python
`hello world` in Python.
:::

:::{tab-item} Rust
`hello world` in Rust.
:::

:::

````

Both styles produce the same HTML structure — a `gp-sphinx-tabs`
container with radio inputs and labels. CSS-only switching, no JS
required for basic functionality.

## Start a new tab-set after the previous

Set `:new-set:` on a `.. tab::` to break the previous run and start a
fresh tab-set, even when the two tabs are adjacent in the source.

```rst
.. tab:: A1

   Belongs to set one.

.. tab:: A2

   Belongs to set one.

.. tab:: B1
   :new-set:

   Starts set two.

.. tab:: B2

   Belongs to set two.
```

This produces two independent tab-sets, each with its own radio
group.
