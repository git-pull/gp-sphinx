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

## Shared layer

`sphinx_typehints_gp` serves as the shared internal annotation normalization
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
