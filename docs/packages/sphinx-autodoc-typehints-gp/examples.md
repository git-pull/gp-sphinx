(sphinx-autodoc-typehints-gp-examples)=

# Examples

```{eval-rst}
.. py:module:: api_demo_typehints_gp
```

The demos below exercise every rendering improvement
`sphinx-autodoc-typehints-gp` ships beyond stock Sphinx + autodoc.
Each section opens with a one-line "what's interesting here", then
shows the rendered output from a small demo module
([`docs/_ext/api_demo_typehints_gp.py`](https://github.com/git-pull/gp-sphinx/blob/main/docs/_ext/api_demo_typehints_gp.py)),
then a callout pointing at the specific HTML shape worth noticing.

## Source-text parameter defaults

`autodoc_preserve_defaults=True` is on by default in
`gp_sphinx.defaults`, so each method's `=…` default renders as the
literal source text rather than the runtime `repr()`. Sentinel
instances like `<api_demo_typehints_gp._DefaultRetry object at
0x…>` become the symbolic name `DEFAULT_RETRY` instead.

## Dataclass `field(default_factory=…)` rendering

The synthetic-init listener walks `dataclasses.fields(...)` after
Sphinx introspects the dataclass and substitutes the factory call's
source text. Stdlib container types render as their literal forms
(`[]`, `{}`, `set()`, `frozenset()`, `()`); named callable factories
render as `Name()`.

```{eval-rst}
.. autoclass:: api_demo_typehints_gp.HookCounters
```

What to look for: the `__init__` signature shows
`alerts=[], index={}, names=set(), tags=(), transports=[]` — no
`<factory>` placeholders.

## Long module-level constants

`GpDataDocumenter` / `GpAttributeDocumenter` route every `:value:`
line through a resolver chain. `TruncateLongRepr(threshold=200)`
collapses long values to `<...truncated, N chars>`; short values
render unchanged.

```{eval-rst}
.. autodata:: api_demo_typehints_gp.SHORT_DEFAULT

.. autodata:: api_demo_typehints_gp.LONG_DEFAULT_RULES
```

What to look for: `SHORT_DEFAULT` shows `'admin'` directly;
`LONG_DEFAULT_RULES` shows `<...truncated, N chars>` instead of the
20-tuple list blob.

## Cross-referenced default values

Stage C's `DefaultValueXrefTransform` walks every
`<span class="default_value">` inside a `<dt>` signature, AST-parses
the text, and turns documented identifier references into clickable
cross-references in the same `<a class="reference internal">
<code class="xref py py-obj">…</code></a>` shape that inline
`:py:obj:` roles produce. Undocumented or unparseable defaults
fall back to plain text.

```{eval-rst}
.. autofunction:: api_demo_typehints_gp.open_session
```

What to look for: the `scope=` and `retry=` defaults link to
{py:attr}`~api_demo_typehints_gp.CacheScope.Session` and
{py:data}`~api_demo_typehints_gp.DEFAULT_RETRY` respectively. Hover
the rendered defaults — they're real anchors, not just styled text.

```{eval-rst}
.. autofunction:: api_demo_typehints_gp.with_lambda_default
```

What to look for: the `callback=lambda: None` default falls back to
plain text inside the `default_value` span — no broken-looking
`<code class="xref">` styling on something that can't link.

## Field-list xref styling

`FieldListXrefStyleTransform` normalises every Python-domain
`pending_xref` inside a field list to a single
`<a><code class="xref py py-class | py-exc">…</code></a>` shape —
the same HTML inline `:py:class:` roles produce. Parameter types,
return types, and raises exception names all match. The whole
`name (type, optional)` prefix on each parameter row is wrapped in
`<span class="gp-sphinx-field-prefix">` so a single CSS rule renders
the prefix in monospace; `Returns` prose stays in body font.

The `open_session` autodoc above already demonstrates this — its
`Parameters`, `Return`, and `Raises` sections each render the
canonical shape on every Python identifier reference.

## Documented targets used by the demos

```{eval-rst}
.. autoclass:: api_demo_typehints_gp.CacheScope
   :members:

.. autoclass:: api_demo_typehints_gp.Transport

.. autoexception:: api_demo_typehints_gp.ConnectionFailure

.. autodata:: api_demo_typehints_gp.DEFAULT_RETRY
```

```{package-reference} sphinx-autodoc-typehints-gp
```
