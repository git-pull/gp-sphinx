(sphinx-ux-tabs-examples)=

# Examples

## Inline-tabs style (consecutive `.. tab::`)

```{eval-rst}
.. tab:: Python

   .. code-block:: python

      def greet(name: str) -> str:
          return f"Hello, {name}!"

.. tab:: Rust

   .. code-block:: rust

      fn greet(name: &str) -> String {
          format!("Hello, {}!", name)
      }

.. tab:: Go

   .. code-block:: go

      func Greet(name string) string {
          return fmt.Sprintf("Hello, %s!", name)
      }
```

## Tab-set style ({tab-set} / {tab-item})

::::{tab-set}

:::{tab-item} pip
```console
$ pip install gp-sphinx
```
:::

:::{tab-item} uv
```console
$ uv add gp-sphinx
```
:::

:::{tab-item} pipx
```console
$ pipx install gp-sphinx
```
:::

::::

## Pre-selected tab

::::{tab-set}

:::{tab-item} Linux
Linux setup instructions.
:::

:::{tab-item} macOS
:selected:
macOS setup instructions — selected on page load.
:::

:::{tab-item} Windows
Windows setup instructions.
:::

::::

## Synchronized tab-sets

Pick a shell here:

::::{tab-set}
:sync-group: shell

:::{tab-item} bash
:sync: bash
```bash
export PATH="$HOME/.local/bin:$PATH"
```
:::

:::{tab-item} zsh
:sync: zsh
```zsh
typeset -U path PATH
path=("$HOME/.local/bin" $path)
```
:::

:::{tab-item} fish
:sync: fish
```fish
fish_add_path "$HOME/.local/bin"
```
:::

::::

The same shell stays selected here:

::::{tab-set}
:sync-group: shell

:::{tab-item} bash
:sync: bash
```bash
source ~/.bashrc
```
:::

:::{tab-item} zsh
:sync: zsh
```zsh
source ~/.zshrc
```
:::

:::{tab-item} fish
:sync: fish
```fish
source ~/.config/fish/config.fish
```
:::

::::

Click a tab in either tab-set; the other follows.

## Size variants

Default size — compact labels at `0.95em`:

::::{tab-set}

:::{tab-item} pip
```console
$ pip install gp-sphinx
```
:::

:::{tab-item} uv
```console
$ uv add gp-sphinx
```
:::

:::{tab-item} pipx
```console
$ pipx install gp-sphinx
```
:::

::::

`:class: gp-sphinx-tabs--large` — body-size labels with roomier
padding:

::::{tab-set}
:class: gp-sphinx-tabs--large

:::{tab-item} pip
```console
$ pip install gp-sphinx
```
:::

:::{tab-item} uv
```console
$ uv add gp-sphinx
```
:::

:::{tab-item} pipx
```console
$ pipx install gp-sphinx
```
:::

::::

## Deep-link to a tab

::::{tab-set}
:sync-group: example

:::{tab-item} Python
:sync: python
```python
print("hello world")
```
:::

:::{tab-item} Rust
:sync: rust
```rust
println!("hello world");
```
:::

:::{tab-item} Go
:sync: go
```go
fmt.Println("hello world")
```
:::

::::

Open this page with <a href="?example=python"><code>?example=python</code></a>
to pre-select the Python tab via the sphinx-design URL form. The
legacy sphinx-inline-tabs form is supported too:
<a href="?tabs=Python"><code>?tabs=Python</code></a>. Either form
writes through to `localStorage`, so the choice persists on subsequent
visits.

## `:new-set:` breaks a consecutive run

```{eval-rst}
.. tab:: Set A, tab 1

   First tab of the first set.

.. tab:: Set A, tab 2

   Second tab of the first set — auto-grouped with the previous.

.. tab:: Set B, tab 1
   :new-set:

   ``:new-set:`` forces a fresh tab-set break.

.. tab:: Set B, tab 2

   Second tab of the second set.
```
