(sphinx-autodoc-docutils-reference)=

# API Reference

## Directive reference

Generated from {py:meth}`~sphinx.application.Sphinx.add_directive`
registrations in
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
| `` {docutils:transform}`Name` `` | {rst:dir}`autotransform` / {rst:dir}`autotransforms` entries |
| `` {docutils:reader}`Name` `` | {rst:dir}`autoreader` / {rst:dir}`autoreaders` entries |
| `` {docutils:parser}`Name` `` | {rst:dir}`autoparser` / {rst:dir}`autoparsers` entries |
| `` {docutils:writer}`Name` `` | {rst:dir}`autowriter` / {rst:dir}`autowriters` entries |
| `` {docutils:node}`Name` `` | {rst:dir}`autonode` / {rst:dir}`autonodes` entries |
| `` {docutils:translator}`Name` `` | {rst:dir}`autotranslator` / {rst:dir}`autotranslators` entries |

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
