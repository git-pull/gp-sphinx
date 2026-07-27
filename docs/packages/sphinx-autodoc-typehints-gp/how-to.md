(sphinx-autodoc-typehints-gp-how-to)=

# How to

Use this extension when autodoc output needs static annotation rendering,
NumPy-style field-list cross-references, and reusable type-display helpers
without importing application-only dependencies.

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

- Resolves type hints statically without `exec()` or {py:func}`typing.get_type_hints`.
- Works with `TYPE_CHECKING` blocks because annotations are stringified at Sphinx build time.
- No text-level race conditions with Napoleon.
- Hides incidental doctest setup marked `# doctest: +HIDE` from rendered
  docstrings, so plumbing can execute without cluttering the example.
- Gives every class-level name — fields, keys, enum members, class
  variables — exactly one description, wherever you wrote it. See
  {ref}`class-level-names`.
- Exposes reusable helpers for annotation display classification and rendered
  type paragraphs used by the other autodoc packages.

(class-level-names)=

## Describing class-level names

A class declares more than methods. `NamedTuple` fields, dataclass fields
including {py:class}`~dataclasses.InitVar`, {py:class}`~typing.TypedDict`
keys, {py:class}`~enum.Enum` members, {py:data}`~typing.ClassVar`
declarations, and plain constants all reach your reference page. Each one
gets its description exactly once, from whichever of three places you
wrote it in.

A NumPy `Attributes` entry in the class docstring is the usual choice,
because it keeps every field's prose together where a reader meets the
class:

```python
class Retry(t.NamedTuple):
    """How often to retry, and how long to wait.

    Attributes
    ----------
    attempts : int
        Total tries, including the first.
    backoff : float
        Seconds multiplied by the attempt number between tries.
    """

    attempts: int
    backoff: float
```

A docstring directly under the assignment, or a `#:` comment above it,
counts equally. Reach for those when a field's explanation is long enough
to crowd the class docstring:

```python
class Limits:
    #: Requests allowed per minute before throttling starts.
    rate: t.ClassVar[int] = 60

    timeout: t.ClassVar[float] = 5.0
    """Seconds to wait for a response before giving up."""
```

Describing a name costs you nothing in the rendered signature. The entry
keeps whatever autodoc computed for it — an enum member still shows its
value, a dataclass field its annotation and its default.

Write the description on the class that *declares* the name. A subclass
that inherits the field inherits the description with it, so a base class
documenting forty fields does not oblige each subclass to repeat them.

### What happens to a name you describe nowhere

A field nobody describes reaches the page as a bare name with a type and
no prose. That is the honest result: the reader can see the field exists
and that nothing was said about it.

A `ClassVar` nobody describes is withheld from the page instead. Class
variables are frequently internal — a registry, a cached sentinel, a
counter — and a reference page listing them bare says less than one that
omits them. The trade-off is that an undescribed class variable goes
missing rather than looking empty, so a name you *meant* to publish
disappears until you describe it. If your project would rather see them
all, turn them back on:

```python
gp_typehints_show_undocumented_class_vars = True
```

## Hiding incidental doctest setup

A docstring example often needs plumbing to run — building an environment
mapping, opening a socket path — that means nothing to the reader. Mark the
setup line with `# doctest: +HIDE` and this extension drops it from the
rendered docstring, together with any `...` continuation lines, leaving the
meaningful call and its output in place:

```python
def connect(url: str) -> Connection:
    """Open a connection to ``url``.

    >>> socket = "/run/gp/app.sock"  # doctest: +HIDE
    >>> connect("unix://" + socket)
    <Connection ...>
    """
```

The rendered page shows only the `connect(...)` call and its result; the
`socket` line is gone. Nothing rewrites the source docstring — the strip runs
at Sphinx build time, on the `autodoc-process-docstring` event — so the example
your doctest runner executes is unchanged.

Because `# doctest: +HIDE` is a doctest optionflag, the runner has to recognize
it: register it once with `doctest.register_optionflag("HIDE")`, or an
unregistered flag raises `ValueError: invalid option '+HIDE'` when the
docstring runs.

## Shared layer

`sphinx_autodoc_typehints_gp` serves as the shared internal annotation normalization
layer for the `sphinx-autodoc-*` family.  The symbols exported in `__all__`
are intended for use by other `gp-sphinx` packages and by extension authors
who want to reuse the same rendering pipeline.  The API is stable within a
`gp-sphinx` version range but does not carry the same backward-compatibility
guarantees as {py:func}`gp_sphinx.config.merge_sphinx_config`.

## Choosing the right helper

Four `build_*` functions span two axes:

| | Resolved (`env` available) | Unresolved (annotation text only) |
|---|---|---|
| Raw paragraph | {py:func}`~sphinx_autodoc_typehints_gp.build_resolved_annotation_paragraph` | {py:func}`~sphinx_autodoc_typehints_gp.build_annotation_paragraph` |
| Display-classified | {py:func}`~sphinx_autodoc_typehints_gp.build_resolved_annotation_display_paragraph` | {py:func}`~sphinx_autodoc_typehints_gp.build_annotation_display_paragraph` |

Use `build_resolved_*` inside `doctree-resolved` event handlers where a
{py:class}`~sphinx.environment.BuildEnvironment` is available. Use `build_*`
when you have only the annotation string.

## Annotation display classification

{py:func}`~sphinx_autodoc_typehints_gp.classify_annotation_display` returns an
{py:class}`~sphinx_autodoc_typehints_gp.AnnotationDisplay` with structured
metadata for UI renderers.  All values below are verified against the installed
package:

| Annotation input | {py:attr}`~sphinx_autodoc_typehints_gp.AnnotationDisplay.text` | {py:attr}`~sphinx_autodoc_typehints_gp.AnnotationDisplay.is_literal_enum` | {py:attr}`~sphinx_autodoc_typehints_gp.AnnotationDisplay.literal_members` |
|---|---|---|---|
| `str` | `"str"` | `False` | `()` |
| `str \| None` | `"str \| None"` | `False` | `()` |
| `str \| None` (`strip_none=True`) | `"str"` | `False` | `()` |
| `Literal['open', 'closed']` | `"'open', 'closed'"` | `True` | `("'open'", "'closed'")` |
| `int \| bool` | `"int \| bool"` | `False` | `()` |

`is_literal_enum=True` lets rendering code produce individual badge chips for
each member rather than a monolithic code string. Centralizing that decision in
{py:func}`~sphinx_autodoc_typehints_gp.classify_annotation_display` keeps
FastMCP, pytest-fixtures, and api-style on the same enum-detection behavior.

## Static resolution

| Approach | `TYPE_CHECKING` block safe | Napoleon text-processing race |
|---|---|---|
| {py:func}`typing.get_type_hints` | No — resolves at import time | Yes — depends on import order |
| `sphinx.util.typing.stringify_annotation()` | Yes — resolves at Sphinx build time | No — no text processing |

This extension uses `sphinx.util.typing.stringify_annotation()` (Sphinx
publishes no cross-reference target for it) to resolve annotations at build
time, making it safe with `TYPE_CHECKING` blocks and eliminating
text-processing races with Napoleon.
