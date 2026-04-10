# sphinx-typehints-gp

Unconventional typehints extension for gp-sphinx.

It is also the shared type-rendering layer for the `sphinx-autodoc-*` family:
annotation normalization, xref-node generation, and late-safe annotation
paragraph helpers all live here.

## Installation

```console
$ pip install sphinx-typehints-gp
```

## Usage

Add `sphinx_typehints_gp` to your `extensions` list in `conf.py`:

```python
extensions = [
    "sphinx_typehints_gp",
]
```

## Features

- Resolves type hints statically without `exec()` or `typing.get_type_hints()`.
- Works perfectly with `TYPE_CHECKING` blocks.
- No text-level race conditions with Napoleon.
- Exposes reusable helpers for annotation display classification and rendered
  type paragraphs used by the other autodoc packages.
