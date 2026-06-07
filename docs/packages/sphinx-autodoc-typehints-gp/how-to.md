(sphinx-autodoc-typehints-gp-how-to)=

# How to

## Installation

```console
$ pip install sphinx-autodoc-typehints-gp
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

- Resolves type hints statically without `exec()` or {func}`typing.get_type_hints`.
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
| Raw paragraph | {func}`~sphinx_autodoc_typehints_gp.build_resolved_annotation_paragraph` | {func}`~sphinx_autodoc_typehints_gp.build_annotation_paragraph` |
| Display-classified | {func}`~sphinx_autodoc_typehints_gp.build_resolved_annotation_display_paragraph` | {func}`~sphinx_autodoc_typehints_gp.build_annotation_display_paragraph` |

Use `build_resolved_*` inside `doctree-resolved` event handlers where a
`BuildEnvironment` is available.  Use `build_*` when you have only the
annotation string.

## Annotation display classification

{func}`~sphinx_autodoc_typehints_gp.classify_annotation_display` returns an
{class}`~sphinx_autodoc_typehints_gp.AnnotationDisplay` with structured
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
{func}`~sphinx_autodoc_typehints_gp.classify_annotation_display` so no
downstream package re-implements enum detection heuristics.

## Static resolution

| Approach | `TYPE_CHECKING` block safe | Napoleon text-processing race |
|---|---|---|
| {func}`typing.get_type_hints` | No — resolves at import time | Yes — depends on import order |
| `sphinx.util.typing.stringify_annotation()` | Yes — resolves at Sphinx build time | No — no text processing |

This extension uses `sphinx.util.typing.stringify_annotation()` (Sphinx
publishes no cross-reference target for it) to resolve annotations at build
time, making it safe with `TYPE_CHECKING` blocks and eliminating
text-processing races with Napoleon.
