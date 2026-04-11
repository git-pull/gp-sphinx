# sphinx-typehints-gp

Single-package replacement for `sphinx-autodoc-typehints` and
`sphinx.ext.napoleon` — resolves annotations statically at build time,
no monkey-patching required.

Part of the [gp-sphinx](https://github.com/git-pull/gp-sphinx) shared
autodoc stack: annotation normalization, cross-referenced type links, and
`TYPE_CHECKING`-safe resolution all live here.

## Install

```console
$ pip install sphinx-typehints-gp
```

## Usage

```python
extensions = ["sphinx.ext.autodoc", "sphinx_typehints_gp"]

# Required: makes autodoc insert type annotations into parameter descriptions.
# Without this, the type cross-referencing pipeline fires but has nothing to attach to.
autodoc_typehints = "description"
```

## Features

- Resolves type hints statically via AST — no `exec()`, no `typing.get_type_hints()`.
- Handles `TYPE_CHECKING` blocks correctly (import-time guards are not evaluated).
- No text-processing races with `sphinx.ext.napoleon`.
- Shared annotation normalization and rendering helpers for the `sphinx-autodoc-*` family.

## Documentation

See the [full documentation](https://gp-sphinx.git-pull.com/packages/sphinx-typehints-gp/)
for the API reference, helper functions, and the static resolution comparison table.
