# sphinx-ux-tabs

CSS-only tabbed-content directives under the `gp-sphinx-tabs` CSS
namespace. The package is a first-party drop-in for the
`.. tab::` directive shipped by sphinx-inline-tabs and the
`.. tab-set::` / `.. tab-item::` directives shipped by sphinx-design,
emitting a single radio-input HTML structure that both authoring
styles share.

The bundled JavaScript syncs tab selection across same-`:sync:`
groups and re-binds itself after every gp-sphinx SPA navigation
via the `gp-sphinx:navigated` event from `sphinx-gp-theme`.

## Install

```console
$ pip install sphinx-ux-tabs
```

## Usage

Add the extension to your `conf.py`:

```python
extensions = ["sphinx_ux_tabs"]
```

Then write tabs in either reStructuredText (sphinx-inline-tabs style):

```rst
.. tab:: Python

   Python content.

.. tab:: Rust

   Rust content.
```

…or MyST + sphinx-design style:

```markdown
::::{tab-set}

:::{tab-item} Python
Python content.
:::

:::{tab-item} Rust
:selected:
Rust content.
:::

::::
```
