(sphinx-autodoc-docutils-reference)=

# API Reference

## Directive reference

Generated from `app.add_directive()` registrations in
[`sphinx_autodoc_docutils/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-docutils/src/sphinx_autodoc_docutils/__init__.py)
via the package's own bulk directive — every `auto*` pair documents
itself.

```{eval-rst}
.. autodirectives:: sphinx_autodoc_docutils
```

## Cross-reference roles

The extension registers a `docutils` Sphinx domain. Every component
entry rendered without `:no-index:` becomes a link target for the
matching role:

| Role | Links to |
| --- | --- |
| `` {docutils:transform}`Name` `` | `autotransform` / `autotransforms` entries |
| `` {docutils:reader}`Name` `` | `autoreader` / `autoreaders` entries |
| `` {docutils:parser}`Name` `` | `autoparser` / `autoparsers` entries |
| `` {docutils:writer}`Name` `` | `autowriter` / `autowriters` entries |
| `` {docutils:node}`Name` `` | `autonode` / `autonodes` entries |
| `` {docutils:translator}`Name` `` | `autotranslator` / `autotranslators` entries |

Targets accept the fully-qualified dotted path
(`` {docutils:transform}`pkg.transforms.Sanitize` ``) or the bare class
name when it is unambiguous across the project. Dangling references
warn at build time.

The domain also ships a grouped components index:
{ref}`docutils-componentindex`.

## Extension entry point

```{eval-rst}
.. autofunction:: sphinx_autodoc_docutils.setup
```
