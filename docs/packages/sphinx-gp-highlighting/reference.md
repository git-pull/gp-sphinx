(sphinx-gp-highlighting-reference)=

# Reference

[`sphinx_gp_highlighting/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-highlighting/src/sphinx_gp_highlighting/__init__.py).

## Registered surface

```{package-reference} sphinx-gp-highlighting
```

## Lexers

`sphinx-gp-highlighting` registers these Pygments aliases:

| Alias | Purpose |
| --- | --- |
| `tree` | Preferred directory-tree fence name |
| `directory-tree` | Explicit directory-tree alias |
| `dir-tree` | Short directory-tree alias |

## Config values

.. autoconfigvalues:: sphinx_gp_highlighting

## Roles

.. autoroles:: sphinx_gp_highlighting

## API

.. autofunction:: sphinx_gp_highlighting.setup

.. autoclass:: sphinx_gp_highlighting.lexers.DirectoryTreeLexer

.. autofunction:: sphinx_gp_highlighting.inline.classify_inline_literal

.. autofunction:: sphinx_gp_highlighting.inline.build_highlighted_literal
