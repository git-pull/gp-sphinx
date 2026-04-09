# sphinx-typehints-gp

Unconventional typehints extension for gp-sphinx.

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
