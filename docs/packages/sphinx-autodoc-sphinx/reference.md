(sphinx-autodoc-sphinx-reference)=

# API Reference

## Directive reference

Generated from `app.add_directive()` registrations in
[`sphinx_autodoc_sphinx/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-sphinx/src/sphinx_autodoc_sphinx/__init__.py)
via `sphinx-autodoc-docutils` — a meta-loop where the package that
documents config values uses its sibling package to document its own
directives.

```{eval-rst}
.. autodirectives:: sphinx_autodoc_sphinx
```

## Cross-reference roles

The extension registers a `sphinxext` Sphinx domain. Every component
entry rendered without `:no-index:` becomes a link target for the
matching role:

| Role | Links to |
| --- | --- |
| `` {sphinxext:builder}`Name` `` | `autobuilder` / `autobuilders` entries |
| `` {sphinxext:domain}`Name` `` | `autodomain` / `autodomains` entries |

Targets accept the fully-qualified dotted path
(`` {sphinxext:builder}`pkg.builders.ZipBuilder` ``) or the bare class
name when it is unambiguous across the project. Dangling references
warn at build time.

The domain also ships a grouped components index:
{ref}`sphinxext-componentindex`.
