(sphinx-autodoc-typehints-gp)=

# sphinx-autodoc-typehints-gp

```{gp-sphinx-package-meta} sphinx-autodoc-typehints-gp
```

:::{admonition} Alpha
:class: warning

Rendered output is stable. The Python API, CSS class names, and Sphinx
config value names may change without a major version bump. Pin your
dependency to a specific version range in production.
:::

Single-package replacement for `sphinx-autodoc-typehints` and `sphinx.ext.napoleon`
— resolves annotations statically at build time, no monkey-patching required.

It is also the shared type-rendering layer for the `sphinx-autodoc-*` family:
annotation normalization, xref-node generation, and late-safe annotation
paragraph helpers all live here.

## Installation

```console
$ pip install sphinx-autodoc-typehints-gp
```

## Working usage examples

Add `sphinx_autodoc_typehints_gp` to your `extensions` list in `conf.py`:

```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints_gp",
]

# Required: makes autodoc insert type annotations into parameter descriptions.
# Without this, the type cross-referencing pipeline fires but has nothing to attach to.
autodoc_typehints = "description"
```

## Pipeline position

Two hooks run independently:

| Event | Hook | Priority |
|-------|------|----------|
| `autodoc-process-docstring` | NumPy section parser | default (not priority-controlled) |
| `object-description-transform` | `merge_typehints` | **499** — before Sphinx's built-in `_merge_typehints` at 500 |

Running at priority 499 means cross-referenced `:type:`/`:rtype:` fields are
already in place before Sphinx's built-in handler runs. The built-in sees them
and skips its own plain-text duplicates — cooperation, not conflict.

## Features

- Resolves type hints statically without `exec()` or `typing.get_type_hints()`.
- Works perfectly with `TYPE_CHECKING` blocks.
- No text-level race conditions with Napoleon.
- Exposes reusable helpers for annotation display classification and rendered
  type paragraphs used by the other autodoc packages.

## Shared layer

`sphinx_autodoc_typehints_gp` serves as the shared internal annotation normalization
layer for the `sphinx-autodoc-*` family.  The symbols exported in `__all__`
are intended for use by other `gp-sphinx` packages and by extension authors
who want to reuse the same rendering pipeline.  The API is stable within a
`gp-sphinx` version range but does not carry the same backward-compatibility
guarantees as `gp_sphinx.merge_sphinx_config()`.

## Choosing the right helper

Four `build_*` functions span two axes:

| | Resolved (`env` available) | Unresolved (annotation text only) |
|---|---|---|
| Raw paragraph | `build_resolved_annotation_paragraph` | `build_annotation_paragraph` |
| Display-classified | `build_resolved_annotation_display_paragraph` | `build_annotation_display_paragraph` |

Use `build_resolved_*` inside `doctree-resolved` event handlers where a
`BuildEnvironment` is available.  Use `build_*` when you have only the
annotation string.

## Annotation display classification

`classify_annotation_display()` returns an `AnnotationDisplay` with structured
metadata for UI renderers.  All values below are verified against the installed
package:

| Annotation input | `text` | `is_literal_enum` | `literal_members` |
|---|---|---|---|
| `str` | `"str"` | `False` | `()` |
| `str \| None` | `"str \| None"` | `False` | `()` |
| `str \| None` (`strip_none=True`) | `"str"` | `False` | `()` |
| `Literal['open', 'closed']` | `"'open', 'closed'"` | `True` | `("'open'", "'closed'")` |
| `int \| bool` | `"int \| bool"` | `False` | `()` |

`is_literal_enum=True` lets rendering code produce individual badge chips for
each member rather than a monolithic code string.  This decision used to live
in each consumer (FastMCP, pytest-fixtures, api-style); now it lives in
`classify_annotation_display()` so no downstream package re-implements enum
detection heuristics.

## Static resolution

| Approach | `TYPE_CHECKING` block safe | Napoleon text-processing race |
|---|---|---|
| `typing.get_type_hints()` | No — resolves at import time | Yes — depends on import order |
| `sphinx_stringify_annotation()` | Yes — resolves at Sphinx build time | No — no text processing |

This extension uses `sphinx_stringify_annotation()` to resolve annotations at
build time, making it safe with `TYPE_CHECKING` blocks and eliminating
text-processing races with Napoleon.

## Live demos

Type annotations are cross-referenced automatically. The function below uses
`str`, `int`, and `str` — each becomes a clickable `py:class` link in the
rendered output.

```{eval-rst}
.. autofunction:: api_demo_layout.compact_function
   :noindex:
```

```{package-reference} sphinx-autodoc-typehints-gp
```
